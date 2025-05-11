from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, FilePath, model_validator

from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("config")


class ConfigFileMCPServerEntry(BaseModel):
    name: str = Field(..., description="The name of the MCP server.")
    command: str = Field(..., description="The command to start the MCP server.")
    args: list[str] = Field(..., description="The arguments to pass to the MCP server.")
    env: dict[str, str] = Field(..., description="The environment variables to set for the MCP server.")
    disabled: bool = Field(..., description="Whether the MCP server is disabled.")


class ConfigFileCommandEntry(BaseModel):
    name: str = Field(..., description="The name of the command.")
    description: str = Field(
        ...,
        description="The description of the command. The LLM will use this to determine if the command is relevant to the user's request.",
    )
    prompt: str | None = Field(None, description="The prompt to use if this command is selected. ")
    prompt_file: FilePath | None = Field(None, description="The path to a file containing the prompt to use if this command is selected.")
    allowed_tools: list[str] = Field(default_factory=list, description="The list of tools that the command can use.")
    example_flow: str | None = Field(None, description="An example flow of the command.")

    @model_validator(mode="after")
    def only_one_prompt_source(self) -> Self:
        if not self.prompt and not self.prompt_file:
            msg = "At least one of prompt or prompt_file must be provided"
            raise ValueError(msg)
        if self.prompt and self.prompt_file:
            msg = "Only one of prompt or prompt_file can be provided"
            raise ValueError(msg)
        return self

    def apply_globally_allowed_tools(self, allowed_tools: list[str]) -> Self:
        """Apply globally allowed tools to the command."""
        intersection = set(self.allowed_tools) & set(allowed_tools)

        logger.debug(f"Applying globally allowed tools to command {self.name}: {intersection}")

        return self.model_copy(update={"allowed_tools": list(intersection)})

    def apply_tool_restrictions(self, only_allow_these_tools: list[str]) -> Self:
        """Apply tool restrictions to the command.

        Args:
            only_allow_these_tools: The list of tools that the command can use.
        """

        intersection = set(self.allowed_tools) & set(only_allow_these_tools)

        logger.debug(f"Applying tool restrictions to command {self.name}: {intersection}")

        return self.model_copy(update={"allowed_tools": list(intersection)})


class ConfigFile(BaseModel):
    activation_keywords: list[str] = Field(default_factory=list, description="The list of activation keywords to enable Gemini for GitHub.")
    globally_allowed_tools: list[str] = Field(
        default_factory=list, description="The list of tools that are allowed to be used in all commands."
    )
    mcp_servers: list[ConfigFileMCPServerEntry] = Field(
        default_factory=list, description="The list of MCP servers that can be used in all commands."
    )
    commands: list[ConfigFileCommandEntry] = Field(..., description="The list of commands that can be used.")
    system_prompt: str = Field(..., description="The system prompt to use for all commands.")


class Command(BaseModel):
    name: str = Field(..., description="The name of the command.")
    description: str = Field(
        ...,
        description="The description of the command. The LLM will use this to determine if the command is relevant to the user's request.",
    )
    prompt: str = Field(..., description="The prompt to use if this command is selected. ")
    allowed_tools: list[str] = Field(..., description="The list of tools that the command can use.")
    example_flow: str | None = Field(None, description="An example flow of the command.")

    @classmethod
    def from_config_file_command_entry(
        cls,
        config_file_command_entry: ConfigFileCommandEntry,
        additional_tools: list[str] | None = None,
        tool_restrictions: list[str] | None = None,
    ) -> Self:
        """Create a ConfigCommandEntry instance from a ConfigFileCommandEntry instance.

        Args:
            config_file_command_entry: The ConfigFileCommandEntry instance to create the ConfigCommandEntry instance from.
            additional_tools: An optional list of tools to add to the command.
            tool_restrictions: An optional list of tools to restrict the command to.
        """

        prompt: str

        if config_file_command_entry.prompt:
            prompt = config_file_command_entry.prompt

        if config_file_command_entry.prompt_file:
            with Path(config_file_command_entry.prompt_file).open("r") as f:
                prompt = f.read()

        tools = config_file_command_entry.allowed_tools

        if additional_tools:
            tools.extend(additional_tools)

        if tool_restrictions:
            tools = [tool for tool in tools if tool in tool_restrictions]

        return cls(
            name=config_file_command_entry.name,
            description=config_file_command_entry.description,
            prompt=prompt,
            allowed_tools=tools,
            example_flow=config_file_command_entry.example_flow,
        )


class MCPServerConfiguration(BaseModel):
    name: str = Field(..., description="The name of the MCP server.")
    command: str = Field(..., description="The command to start the MCP server.")
    args: list[str] = Field(..., description="The arguments to pass to the MCP server.")
    env: dict[str, str] = Field(..., description="The environment variables to set for the MCP server.")
    disabled: bool = Field(..., description="Whether the MCP server is disabled.")

    @classmethod
    def from_config_file_mcp_server_entry(cls, config_file_mcp_server_entry: ConfigFileMCPServerEntry) -> Self:
        return cls(**config_file_mcp_server_entry.model_dump())


class Config(BaseModel):
    activation_keywords: list[str] = Field(..., description="The list of activation keywords to enable Gemini for GitHub.")
    commands: list[Command] = Field(..., description="The list of commands that can be used.")
    system_prompt: str = Field(..., description="The system prompt to use for all commands.")
    mcp_servers: list[MCPServerConfiguration] = Field(..., description="The list of MCP servers that can be used.")

    @classmethod
    def from_config_file(
        cls,
        config_file: ConfigFile,
        tool_restrictions: list[str] | None = None,
        command_restrictions: list[str] | None = None,
        activation_keywords: list[str] | None = None,
    ) -> Self:
        """Create a Config instance from a ConfigFile instance.

        Args:
            config_file: The ConfigFile instance to create the Config instance from.
            tool_restrictions: An optional list of tools to restrict the commands to.
        """
        return cls(
            activation_keywords=activation_keywords or config_file.activation_keywords,
            system_prompt=config_file.system_prompt,
            mcp_servers=[MCPServerConfiguration.from_config_file_mcp_server_entry(mcp_server) for mcp_server in config_file.mcp_servers],
            commands=[
                Command.from_config_file_command_entry(
                    cmd,
                    additional_tools=config_file.globally_allowed_tools,
                    tool_restrictions=tool_restrictions,
                )
                for cmd in config_file.commands
                if not command_restrictions or cmd.name in command_restrictions
            ],
        )

    def get_command_by_name(self, name: str) -> Command | None:
        """Get a command by name."""
        return next((cmd for cmd in self.commands if cmd.name == name), None)

    def matches_activation_keyword(self, text: str, restrictions: list[str] | None = None) -> bool:
        """Check if the text matches any of the activation keywords."""

        allowed_activation_keywords = self.activation_keywords.copy()

        if restrictions:
            allowed_activation_keywords = [keyword for keyword in allowed_activation_keywords if keyword in restrictions]

        return any(text.lower().startswith(keyword.lower()) for keyword in allowed_activation_keywords)

    def command_name_to_description_dict(self) -> dict[str, str]:
        """Get a dictionary of command names to descriptions."""
        return {cmd.name: cmd.description for cmd in self.commands}
