import asyncio
import json
from collections.abc import Callable
from enum import Enum
import sys
from typing import Any, Literal

from google.api_core.retry import if_transient_error
from google.api_core.retry_async import AsyncRetry
from google.genai.client import AsyncClient, Client
from google.genai.errors import ClientError, ServerError
from google.genai.types import (
    Content,
    ContentListUnion,
    FunctionCall,
    FunctionCallingConfig,
    FunctionCallingConfigMode,
    FunctionDeclaration,
    FunctionResponse,
    GenerateContentConfig,
    GenerateContentResponse,
    GoogleSearch,
    HarmBlockThreshold,
    HarmCategory,
    Part,
    SafetySetting,
    ThinkingConfig,
    Tool,
    ToolConfig,
)
from pydantic import BaseModel, TypeAdapter

from gemini_for_github.errors.genai import (
    GenAITaskUnknownStatusError,
)
from gemini_for_github.shared.logging import BASE_LOGGER

QUOTA_EXCEEDED_ERROR_CODE = 429
MODEL_OVERLOADED_ERROR_CODE = 503
INTERNAL_ERROR_CODE = 500

MAX_ITERATIONS = 15


def is_retryable(e) -> bool:
    if if_transient_error(e):
        logger.warning(f"Retrying due to transient error: {e}")
        return True
    if isinstance(e, ClientError) and e.code == QUOTA_EXCEEDED_ERROR_CODE:
        logger.warning(f"Retrying due to quota exceeded: {e}")
        return True
    if isinstance(e, ServerError) and e.code == MODEL_OVERLOADED_ERROR_CODE:
        logger.warning(f"Retrying due to model overloaded: {e}")
        return True
    if isinstance(e, ServerError) and e.code == INTERNAL_ERROR_CODE:
        logger.warning(f"Retrying due to internal error: {e}")
        return True
    return False


logger = BASE_LOGGER.getChild("genai")


class GenerationMode(Enum):
    HYBRID = FunctionCallingConfigMode.AUTO
    TOOL_CALLING = FunctionCallingConfigMode.ANY


type GenAITaskResult = GenAITaskFailure | GenAITaskSuccess


class GenAITaskFailure(BaseModel):
    success: Literal[False] = False
    task_details: str
    failure_details: str
    response: GenerateContentResponse


class GenAITaskSuccess(BaseModel):
    success: Literal[True] = True
    task_details: str
    completion_details: str
    response: GenerateContentResponse


class GenAIClient:
    """
    A client for interacting with Google's Generative AI models (e.g., Gemini).
    It handles content generation, tool calling, and retry logic for API requests.
    """

    request_counter: int = 0
    declared_tools: dict[str, tuple[Tool, Callable[..., Any]]]

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-preview-04-17", temperature: float = 0.2, thinking: bool = True):
        """Initialize the GenAI client.

        Args:
            api_key: Google AI API key.
            model: Name of the specific Gemini model to use (e.g., "gemini-2.5-flash-preview-04-17").
            temperature: Model temperature for controlling randomness in generation.
        """

        self.client: AsyncClient = Client(api_key=api_key).aio

        self.model: str = model
        self.temperature = temperature
        self.thinking = thinking
        self.declared_tools = {}
        self.native_tools: dict[str, Tool] = {
            "google_search": GoogleSearch(),  # type: ignore
        }
        self.tool_call_history = []

        self.register_tool("report_completion", self.report_completion)
        self.register_tool("report_failure", self.report_failure)

    def report_completion(self, task_details: str, completion_details: str) -> GenAITaskSuccess:
        """
        Reports that the assigned task has been successfully completed.

        This tool should *only*  be called when it has fully addressed the user's request
        and no further actions are needed. This signals the end of the task execution flow.

        Args:
            task_details: A summary description of the original task assigned by the user.
                          Example: "Refactor the authentication module."
            completion_details: A description of how the task was completed and the final outcome.
                                Example: "Refactored auth module to use JWT, updated tests, all passing."

        Returns:
            GenAITaskSuccess: An object indicating successful task completion. This is typically
                              handled internally by the client to stop the execution loop.
                              (Note: This method actually raises NotImplementedError as it's meant
                               to be intercepted by the calling logic, not executed directly).
        """
        msg = "Not implemented"
        raise NotImplementedError(msg)

    def report_failure(self, task_details: str, failure_details: str) -> GenAITaskFailure:
        """
        Reports that the assigned task could not be completed successfully.

        Call this tool when it determines it cannot fulfill the user's request
        due to errors, limitations, or ambiguities it cannot resolve. This signals an
        unsuccessful end to the task execution flow.

        Args:
            task_details: A summary description of the original task assigned by the user.
                          Example: "Deploy the application to the staging server."
            failure_details: A description of why the task failed.
                             Example: "Deployment failed due to missing credentials in the environment."

        Returns:
            GenAITaskFailure: An object indicating task failure. This is typically
                              handled internally by the client to stop the execution loop.
                              (Note: This method actually raises NotImplementedError as it's meant
                               to be intercepted by the calling logic, not executed directly).
        """
        msg = "Not implemented"
        raise NotImplementedError(msg)

    def get_tool_call_history(self) -> list[str]:
        return self.tool_call_history

    def register_tool_with_declaration(self, name: str, function: Callable[..., Any], function_declaration: FunctionDeclaration):
        tool = Tool(function_declarations=[function_declaration])
        self.declared_tools[name] = (tool, function)

    def add_native_tool(self, name: str, tool: Tool):
        self.native_tools[name] = tool

    def register_tool(self, name: str, function: Callable[..., Any]):
        """
        Registers a Python function as a tool available to the LLM, automatically generating the schema.

        This is the preferred method for registering most custom tools. It infers the tool's
        description from the function's docstring and the parameter schema from its type hints
        (using Pydantic's `TypeAdapter`).

        Args:
            name: The name the LLM will use to call this tool. Should match the Python function name
                  unless there's a specific reason to differ.
            function: The Python callable (function or method) to execute. Must have type hints
                      for its arguments and a clear docstring explaining its purpose, arguments,
                      and what it returns.
        """
        schema = TypeAdapter(function).json_schema()
        schema.pop("additionalProperties")

        self.register_tool_with_declaration(
            name,
            function,
            FunctionDeclaration(
                name=name,
                description=function.__doc__,
                parameters=schema,  # type: ignore
            ),
        )

    def _debug(self, msg: str):
        logger.debug(f"Request {self.request_counter}: {msg}")

    async def _handle_function_call(self, function_name: str, function_args: dict[str, Any] | None) -> FunctionResponse:
        """Handle a function call from the model and return the response.

        Args:
            function_call: The function call object from the model
            tools: The available tools for the model to use

        Returns:
            FunctionResponse: The response from the function call
        """
        tool_function: Callable[..., Any]
        _, tool_function = self.declared_tools[function_name]

        function_args = function_args or {}

        try:
            if asyncio.iscoroutinefunction(tool_function):
                output = await tool_function(**function_args)
            else:
                output = tool_function(**function_args)

        except Exception as e:
            msg = f"Error executing function {function_name}: {e}"
            logger.exception(msg)
            return FunctionResponse(name=function_name, response={"error": str(e)})

        return FunctionResponse(name=function_name, response={"output": output})

    def _handle_completion(self, args: dict[str, Any] | None, response: GenerateContentResponse) -> GenAITaskSuccess:
        if not args:
            msg = "No arguments provided for completion function call"
            logger.error(msg)
            raise GenAITaskUnknownStatusError(msg)

        task_details = args.get("task_details")
        completion_details = args.get("completion_details")

        if not task_details or not completion_details:
            msg = "Task details and completion details are required"
            logger.error(msg)
            raise GenAITaskUnknownStatusError(msg)

        return GenAITaskSuccess(
            task_details=task_details,
            completion_details=completion_details,
            response=response,
        )

    def _handle_failure(self, args: dict[str, Any] | None, response: GenerateContentResponse) -> GenAITaskFailure:
        if not args:
            msg = "No arguments provided for failure function call"
            logger.error(msg)
            raise GenAITaskUnknownStatusError(msg)

        task_details = args.get("task_details")
        failure_details = args.get("failure_details")

        if not task_details or not failure_details:
            msg = "Task details and failure details are required"
            logger.error(msg)
            raise GenAITaskUnknownStatusError(msg)

        return GenAITaskFailure(
            task_details=task_details,
            failure_details=failure_details,
            response=response,
        )

    def _get_safety_settings(self) -> list[SafetySetting]:
        return [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            )
        ]

    def _detect_function_call(self, response: GenerateContentResponse) -> FunctionCall | None:
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]

            if not candidate.content or not candidate.content.parts:
                return None

            for part in candidate.content.parts:
                if not part.function_call:
                    continue
                return part.function_call

        return None

    def _get_generate_content_config(self, system_prompt: str, tools: list[Tool] | None = None) -> GenerateContentConfig:
        safety_settings = self._get_safety_settings()

        return GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=4096,
            tools=tools,  # type: ignore
            safety_settings=safety_settings,
            system_instruction=system_prompt,
            thinking_config=ThinkingConfig(thinking_budget=2048) if self.thinking else None,
            tool_config=ToolConfig(
                function_calling_config=FunctionCallingConfig(mode=FunctionCallingConfigMode.ANY),
            ),
        )

    def get_allowed_tools(self, tool_names: list[str]) -> list[tuple[str, Tool]]:
        allowed_tools = []

        reduced_and_sorted_tool_names = sorted(set(tool_names))

        for name in reduced_and_sorted_tool_names:
            if name in self.declared_tools:
                allowed_tools.append((name, self.declared_tools[name][0]))
            elif name in self.native_tools:
                allowed_tools.append((name, self.native_tools[name]))
            else:
                raise ValueError(f"Tool {name} not found")
        return allowed_tools

    def log_conversation_summary(self, contents: list[Content]):
        for index, content in enumerate(contents):
            if not content.role or not content.parts:
                continue

            role: str = content.role
            parts: list[Part] = content.parts

            for part in parts:
                content_summary = {}

                if part.text:
                    content_summary["text"] = part.text[:20]
                if part.function_call:
                    content_summary["function_call"] = part.function_call.name
                    content_summary["function_call_args"] = self._trim_call_args(part.function_call.args or {})
                if part.function_response:
                    content_summary["function_response"] = part.function_response.name

            logger.info(f"{index}: {role}: {content_summary}")

    @classmethod
    def _trim_call_args(cls, call_args: dict[str, Any]) -> dict[str, Any]:
        trimmed_call_args = {}

        for k, v in call_args.items():
            if isinstance(v, str):
                trimmed_call_args[k] = v[:20]
            else:
                trimmed_call_args[k] = json.dumps(v)[:20]
        return trimmed_call_args

    @AsyncRetry(predicate=is_retryable)
    async def _get_completion(
        self,
        system_prompt: str,
        contents: ContentListUnion,
        tools: list[Tool],
    ) -> GenerateContentResponse:
        generation_config = self._get_generate_content_config(system_prompt, tools)

        self._debug(f"System prompt: {system_prompt}")
        self._debug(f"Contents: {contents}")

        return await self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=generation_config,
        )

    @classmethod
    def new_user_content(cls, user_prompt: str) -> Content:
        return Content(
            role="user",
            parts=[Part(text=user_prompt)],
        )

    @classmethod
    def new_model_content(cls, model_prompt: str) -> Content:
        return Content(
            role="model",
            parts=[Part(text=model_prompt)],
        )

    @classmethod
    def new_model_function_call(cls, function_call: FunctionCall) -> Content:
        return Content(
            role="model",
            parts=[Part(function_call=function_call)],
        )

    @classmethod
    def new_model_function_response(cls, function_response: FunctionResponse) -> Content:
        return Content(
            role="model",
            parts=[Part(function_response=function_response)],
        )
    
    def _print_last_response(self, response: GenerateContentResponse):
        if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
            return

        for part in response.candidates[0].content.parts:
            logger.warning(f"Last response part: {part}")

    async def perform_task(self, system_prompt: str, content_list: list[Content], allowed_tools: list[str]) -> GenAITaskResult:
        """Perform a task using the AI model.

        Args:
            system_prompt: The initial instructions or persona definition for the model.
            content_list: A list of `google.genai.types.Content` objects representing the
                          conversation history (user messages, previous model responses, tool calls/results).
                          Typically starts with the initial user request.
            allowed_tools: A list of strings specifying the names of the tools (registered via
                           `register_tool` or `add_native_tool`) that the model is permitted
                           to use for this specific task. The internal `report_completion` and
                           `report_failure` tools are always implicitly added.

        Returns:
            GenAITaskResult: Either a `GenAITaskSuccess` or `GenAITaskFailure` object,
                             indicating the outcome reported by the model via the respective tools.

        Raises:
            GenAITaskUnknownStatusError: If the model finishes interacting (e.g., max iterations)
                                         without calling `report_completion` or `report_failure`.
            ValueError: If an unknown tool name is provided in `allowed_tools`.
            Other exceptions from the underlying API calls or tool executions.
        """

        iteration = 0

        provided_tool_names: list[str]
        provided_tools: list[Tool]

        provided_tool_names, provided_tools = zip(
            *self.get_allowed_tools([*allowed_tools, "report_completion", "report_failure", *self.native_tools.keys()]), strict=True
        )

        logger.info(f"Performing task with provided tools: {provided_tool_names}")

        while iteration < MAX_ITERATIONS:
            logger.info(f"Model completion iteration {iteration}")

            iteration += 1
            
            response = await self._get_completion(system_prompt=system_prompt, contents=content_list, tools=provided_tools)  # type: ignore

            logger.debug(f"Model completion response: {response}")

            function_call = self._detect_function_call(response)

            if not function_call:
                logger.error("No function call detected. Asking for completion again.")
                self._print_last_response(response)
                continue

            logger.info(f"Function call detected: {function_call.name} with args: {function_call.args}")

            self.tool_call_history.append(function_call.name)

            if not function_call.name:
                msg = "Function call name is missing but tool calls are required. Asking for completion again."
                logger.error(msg)
                self._print_last_response(response)
                continue
                #raise GenAITaskUnknownStatusError(msg)

            if function_call.name == "report_completion":
                self.log_conversation_summary(content_list)
                return self._handle_completion(function_call.args, response)
            if function_call.name == "report_failure":
                self.log_conversation_summary(content_list)
                return self._handle_failure(function_call.args, response)

            function_response = await self._handle_function_call(function_call.name, function_call.args)

            if sys.getsizeof(function_response.response) > 1048576:  # noqa: PLR2004
                logger.warning(f"Function response is too large (>1MB) to be processed: {function_response.response}")
                function_response = FunctionResponse(
                    name=function_call.name,
                    response={
                        "error": "Response is too large to be processed. Perform your tool call in a way that returns less data.",
                    },
                )

            content_list = [
                *list(content_list),  # type: ignore
                Content(role="model", parts=[Part(function_call=function_call)]),
                Content(role="user", parts=[Part(function_response=function_response)]),
            ]

        self.log_conversation_summary(content_list)

        msg = f"Model did not complete task after {MAX_ITERATIONS} iterations"
        raise GenAITaskUnknownStatusError(msg)
