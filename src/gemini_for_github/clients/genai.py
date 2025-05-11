from typing import Any

from google.genai.client import AsyncClient, Client
from google.genai.types import (
    Content,
    FunctionCallingConfig,
    FunctionCallingConfigMode,
    GenerateContentConfig,
    GenerateContentResponse,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
    ToolConfig,
    ToolListUnion,
    ContentListUnion,
    ContentListUnionDict,
)

from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("genai")


class GenAIClient:
    """Concrete implementation of AI model client using Google's Generative AI."""

    request_counter: int = 0

    def __init__(
        self, api_key: str, model: str = "gemini-2.5-flash-preview-04-17", temperature: float = 0.2
    ):
        """Initialize the GenAI client.

        Args:
            api_key: Google AI API key
            model: Name of the model to use
            temperature: Model temperature
        """

        self.client: AsyncClient = Client(api_key=api_key).aio

        self.model: str = model
        self.temperature = temperature

    def _debug(self, msg: str):
        logger.debug(f"Request {self.request_counter}: {msg}")

    async def generate_content(
        self,
        system_prompt: str,
        user_prompts: ContentListUnion | ContentListUnionDict,
        tools: ToolListUnion,
    ) -> dict[str, Any]:
        """Generate content using the AI model.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            tools: Optional list of Tool objects available to the model

        Returns:
            Dictionary containing the generated response
        """

        safety_settings: list[SafetySetting] = [
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

        self.request_counter += 1

        generation_config = GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=4096,
            safety_settings=safety_settings,
            tools=tools,
            system_instruction=system_prompt,
            stop_sequences=["Stop."],
            tool_config=ToolConfig(
                function_calling_config=FunctionCallingConfig(
                    #mode=FunctionCallingConfigMode.ANY,
                )
            ),
        )

        # self._debug(f"Generation config: {generation_config}")
        self._debug(f"User prompts: {user_prompts}")

        response: GenerateContentResponse = await self.client.models.generate_content(
            model=self.model,
            contents=user_prompts,
            config=generation_config,
        )

        self._debug(f"Model response: {response.text}")

        if response.automatic_function_calling_history and len(response.automatic_function_calling_history) > 0:
            self._log_tool_calls(response.automatic_function_calling_history)

        return {"text": response.text, "tool_calls": response.prompt_feedback}

    def _log_tool_calls(self, calling_history: list[Content]):
        for tool_call in calling_history:
            if not tool_call.parts:
                continue

            for part in tool_call.parts:
                if not part.function_call:
                    continue

                self._debug(f"Function Call: {part.function_call.name}({part.function_call.args})")

                if part.function_response:
                    self._debug(f"Function Response: {part.function_response}")
