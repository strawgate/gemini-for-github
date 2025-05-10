
# Direction

Gemini for GitHub is a CLI tool that integrates with GitHub to provide AI-powered assistance for code reviews, issue analysis, and code understanding. It uses Google's Gemini AI model to understand context and provide relevant insights.

Typical usage is driven by github events which trigger Gemini for Github to review the issue or PR and provide feedback directly to the PR or issue. Gemini for Github can either get a diff of the changes from the PR or can investigate the repository directly to identify files and code relevant to the question being asked.

When the user asks for Gemini for Github to improve a PR, add tests, or otherwise interact with the PR, we use Aider to generate the changes and apply them to the PR.

# Overall Architecture

We want Gemini for Github to have two possible entry points, decided by the CLI command used. We want a CLI command specific to it helping with a Github Issue and another for interacting with a Github PR. 

```
commands:
  review_pr:
    description: "Review a pull request"
    prompt: |
      Please review the following code changes and provide feedback:

      {diff}

      Please provide a detailed code review that:
      1. Identifies potential issues or bugs
      2. Suggests improvements for code quality
      3. Checks for security concerns
      4. Verifies best practices are followed
      5. Ensures the changes are well-documented

      Format your response in markdown with clear sections.
```

When the user asks Gemini for Github to review a PR, via the custom activation keyword "bill2.0", "bill2.0 please review the PR for styling", we will call out to Gemini with the user's ask and the currently enabled commands and ask Gemini to select the best command to use. After selecting the best command to use, we will pass the prompt to Gemini with the tools that are enabled for the session (via the cli param) and the mandatory files (via the cli param).


## Flows

### Users asks us to suggest a solution to an issue

1. Customer creates an issue in a repository
2. Developer comments on the issue with "gemini how should we fix this so -- maybe add this as a new type for the handler?" -- note we will let gemini suggest the command to use based on the user's comment and the list of available commands provided by the cli args, we will not try to extract a specific command from the comment.
3. A github action fires which has a definition which triggers Gemini for Github and provides CLI arguments including the issue number,indicating that Gemini can recursively list files, recursively read files, read the issue and comment on the issue and indicates that instantiation can use the following commands: `suggest_solution` from the prompts yaml.
4. Gemini for Github uses the Filesystem Operations tool to identify relevant files in the repository, reads them in bulk, and then suggests a solution
5. Gemini for Github uses the GitHub API to update the issue with suggestions for fixing the issue.

### User asks us to make a change to a PR

1. User comments on a PR with "gemini please add a test for this"
2. A github action fires which has a definition which triggers Gemini for Github and provides CLI arguments including the PR number,indicating that Gemini can recursively list files, recursively read files, read the PR, comment on the PR, write code and make a pr and indicates that instantiation can use the following commands: `suggest_solution` from the prompts yaml.
3. Gemini for Github uses the Filesystem Operations tool to identify relevant files in the repository, reads them in bulk, and then builds a very comprehensive prompt. Gemini then does a tool call to the "write_code" command that the user has allowed via the cli args. That tool call invokes aider with the comprehensive prompt and aider makes a branch, generates and commits the changes. Then Gemini looks at the changes and if it approves it will use the make pr Tool to make a PR for them providing a PR description with link to the original issue etc.

### Key Items in these flows

Tools are written in Python and some of the tools will invoke Aider to generate the changes. We then expose these tools to the Gemini AI model via Automatic Function Calling.

Prompts are not hardcoded, they are in a prompts.yaml file. We will not perform any special actions for any of the commands or flows. We provide the tools and default prompts but the user can define their own commands and prompts via their own prompts yaml file. In this way we are useless without prompts. We are just coordinating. The LLM will decide if we make an issue, update the PR, etc based on what the user says is allowed in that flow via the CLI.

## User-defined Tools

The user can define their own tools via an McpServers yaml file. We will instantiate the user defined MCP servers and then create a dictionary of tool names to declarations of the tool. When we are invoked we will only include tools from the MCP server that are also in the list of allowed tools.



```
import asyncio
import os
from datetime import datetime
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="npx",  # Executable
    args=["-y", "@philschmid/weather-mcp"],  # Weather MCP Server
    env=None,  # Optional environment variables
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Prompt to get the weather for the current day in London.
            prompt = f"What is the weather in London in {datetime.now().strftime('%Y-%m-%d')}?"
            # Initialize the connection between client and server
            await session.initialize()

            # Get tools from MCP session and convert to Gemini Tool objects
            mcp_tools = await session.list_tools()
            tools = [
                types.Tool(
                    function_declarations=[
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                k: v
                                for k, v in tool.inputSchema.items()
                                if k not in ["additionalProperties", "$schema"]
                            },
                        }
                    ]
                )
                for tool in mcp_tools.tools
            ]

            # Send request to the model with MCP function declarations
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    tools=tools,
                ),
            )

            # Check for a function call
            if response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
                print(function_call)
                # Call the MCP server with the predicted tool
                result = await session.call_tool(
                    function_call.name, arguments=function_call.args
                )
                print(result.content[0].text)
                # Continue as shown in step 4 of "How Function Calling Works"
                # and create a user friendly response
            else:
                print("No function call found in the response.")
                print(response.text)

# Start the asyncio event loop and run the main function
asyncio.run(run())
```

## Tools
The tools will be implemented in Python and some of the tools will invoke Aider to generate the changes. We then expose these tools to the Gemini AI model via Automatic Function Calling.

```
Automatic Function Calling (Python Only)
When using the Python SDK, you can provide Python functions directly as tools. The SDK automatically converts the Python function to declarations, handles the function call execution and response cycle for you. The Python SDK then automatically:

Detects function call responses from the model.
Call the corresponding Python function in your code.
Sends the function response back to the model.
Returns the model's final text response.
To use this, define your function with type hints and a docstring, and then pass the function itself (not a JSON declaration) as a tool:

Python

from google import genai
from google.genai import types

# Define the function with type hints and docstring
def get_current_temperature(location: str) -> dict:
    """Gets the current temperature for a given location.

    Args:
        location: The city and state, e.g. San Francisco, CA

    Returns:
        A dictionary containing the temperature and unit.
    """
    # ... (implementation) ...
    return {"temperature": 25, "unit": "Celsius"}

# Configure the client and model
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))  # Replace with your actual API key setup
config = types.GenerateContentConfig(
    tools=[get_current_temperature]
)  # Pass the function itself

# Make the request
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="What's the temperature in Boston?",
    config=config,
)

print(response.text)  # The SDK handles the function call and returns the final text
```

## Aider Tool

We will use Aider to generate changes to the codebase.
```
You can also script aider from python:

from aider.coders import Coder
from aider.models import Model

# This is a list of files to add to the chat
fnames = ["greeting.py"]

model = Model("gpt-4-turbo")

# Create a coder object
coder = Coder.create(main_model=model, fnames=fnames)

# This will execute one instruction on those files and then return
coder.run("make a script that prints hello world")

# Send another instruction
coder.run("make it say goodbye")

# You can run in-chat "/" commands too
coder.run("/tokens")
```

# Current Status

The code is currently in the early stages of development. The code is not yet ready for use. There is unused code, non-functional code, and no usage of aider.

# Next Steps

Read every file in the repo with the Filesystem Operations tool and suggest a plan to get the code aligned with our direction.



## Command Line Arguments

required
click.option("--github-token", envvar="GITHUB_TOKEN", required=True, help="GitHub API token"),
click.option("--github-owner", envvar="GITHUB_OWNER", required=True, help="GitHub repository owner"),
click.option("--github-repo", envvar="GITHUB_REPO", required=True, help="GitHub repository name"),
click.option("--gemini-api-key", envvar="GEMINI_API_KEY", required=True, help="Gemini API key"),

optional
click.option("--github-issue-number", type=int, help="GitHub issue number"),
click.option("--github-pr-number", type=int, help="GitHub pull request number"),

click.option("--model", envvar="GEMINI_MODEL", default="gemini-2.5-flash-preview-04-17", help="Gemini model to use"),
click.option("--activation-keywords", type=str, help="Comma-separated activation keywords (e.g., gemini,bill2.0)"),
click.option("--config-file", type=str, help="Path to the config file"),
click.option("--tool-restrictions", type=str, help="Comma-separated list of tool restrictions"),
click.option("--command-restrictions", type=str, help="Comma-separated list of command restrictions"),
click.option("--debug", is_flag=True, help="Enable debug mode"),