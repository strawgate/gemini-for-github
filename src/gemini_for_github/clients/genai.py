from typing import Any

from google.genai import types
from google.genai.client import AsyncClient, Client
from google.genai.types import ContentListUnion, ContentListUnionDict, HarmBlockThreshold, HarmCategory, SafetySetting, ToolListUnion


class GenAIClient:
    """Concrete implementation of AI model client using Google's Generative AI."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", temperature: float = 0.7, top_p: float = 0.8, top_k: int = 40):
        """Initialize the GenAI client.

        Args:
            api_key: Google AI API key
            model: Name of the model to use
            temperature: Model temperature
            top_p: Model top_p
            top_k: Model top_k
        """

        self.client: AsyncClient = Client(api_key=api_key).aio

        self.model: str = model
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k

    async def generate_content(
        self,
        contents: ContentListUnion | ContentListUnionDict,
        tools: ToolListUnion | None = None,
    ) -> dict[str, Any]:
        """Generate content using the AI model.

        Args:
            contents: List of content parts to process
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

        generation_config = types.GenerateContentConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            max_output_tokens=2048,
            safety_settings=safety_settings,
            tools=tools,
        )

        # Generate the response
        response = await self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=generation_config,
        )

        return {"text": response.text, "tool_calls": response.prompt_feedback}
