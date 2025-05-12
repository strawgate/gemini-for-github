import asyncio
from collections.abc import Callable
from enum import Enum
from typing import Any, Literal

from google.api_core.retry import if_transient_error
from google.api_core.retry_async import AsyncRetry
from google.genai.client import AsyncClient, Client
from google.genai.errors import ClientError, ServerError
from google.genai.types import (
    Content,
    ContentListUnion,
    ContentUnion,
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
    GenAIToolFunctionError,
)
from gemini_for_github.shared.logging import BASE_LOGGER

QUOTA_EXCEEDED_ERROR_CODE = 429
MODEL_OVERLOADED_ERROR_CODE = 503

MAX_ITERATIONS = 10


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
            "google_search": GoogleSearch(), # type: ignore
        }
        self.tool_call_history = []

        self.register_tool("report_completion", self.report_completion)
        self.register_tool("report_failure", self.report_failure)

    def report_completion(self, task_details: str, completion_details: str) -> GenAITaskSuccess:
        """Reporting completion indicates that the model has completed the task. The model should only
        call this tool when it is sure it has completed the user's original task.

        Args:
            task_details: Details about the task the user requested.
            completion_details: Details about how the model completed that task from the user.

        Returns:
            GenAITaskSuccess: A success response.
        """
        msg = "Not implemented"
        raise NotImplementedError(msg)

    def report_failure(self, task_details: str, failure_details: str) -> GenAITaskFailure:
        """Reporting failure indicates that the model has failed to complete the task. The model should only
        call this tool when it is sure it has failed to complete the user's original task.

        Args:
            task_details: Details about the task the user requested.
            failure_details: Details about how the model failed to complete that task from the user.

        Returns:
            GenAITaskFailure: A failure response.
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
                result = await tool_function(**function_args)
            else:
                result = tool_function(**function_args)

        except Exception as e:
            msg = f"Error executing function {function_name}: {e}"
            logger.exception(msg)
            raise GenAIToolFunctionError(msg) from e

        return FunctionResponse(name=function_name, response={"result": result})

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
        for name in tool_names:
            if name in self.declared_tools:
                allowed_tools.append((name, self.declared_tools[name][0]))
            elif name in self.native_tools:
                allowed_tools.append((name, self.native_tools[name]))
            else:
                raise ValueError(f"Tool {name} not found")
        return allowed_tools

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

    async def perform_task(self, system_prompt: str, user_prompts: list[str], allowed_tools: list[str]) -> GenAITaskResult:
        """Perform a task using the AI model.

        Args:
            system_prompt: System prompt.
            user_prompts: A list of user prompts or a dictionary of content parts.
            tools: Optional list of Tool objects available to the model.
            check_completion: Whether to check if the model completed its task.

        Returns:
            str: The generated response text
        """

        content_list: ContentUnion = [
            Content(
                role="user",
                parts=[Part(text=user_prompt)],
            )
            for user_prompt in user_prompts
        ]  # type: ignore

        iteration = 0

        provided_tool_names: list[str]
        provided_tools: list[Tool]

        provided_tool_names, provided_tools = zip(
            *self.get_allowed_tools([*allowed_tools, "report_completion", "report_failure", *self.native_tools.keys()]), strict=True
        )

        logger.info(f"Performing task with provided tools: {provided_tool_names}")

        while iteration < MAX_ITERATIONS:
            logger.info(f"Model completion iteration {iteration}")
            response = await self._get_completion(system_prompt=system_prompt, contents=content_list, tools=provided_tools)  # type: ignore

            logger.debug(f"Model completion response: {response}")

            function_call = self._detect_function_call(response)

            if not function_call:
                logger.info("No function call detected")
                break

            logger.info(f"Function call detected: {function_call.name} with args: {function_call.args}")

            self.tool_call_history.append(function_call.name)

            if not function_call.name:
                msg = "Function call name is required"
                logger.error(msg)
                raise GenAITaskUnknownStatusError(msg)

            if function_call.name == "report_completion":
                return self._handle_completion(function_call.args, response)
            if function_call.name == "report_failure":
                return self._handle_failure(function_call.args, response)

            function_response = await self._handle_function_call(function_call.name, function_call.args)

            content_list = [
                *list(content_list),  # type: ignore
                Content(role="model", parts=[Part(function_call=function_call)]),
                Content(role="user", parts=[Part(function_response=function_response)]),
            ]
            iteration += 1

        return response
