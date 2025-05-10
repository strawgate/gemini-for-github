import logging
from typing import Self

from pydantic import AliasChoices, BaseModel, Field, FilePath, model_validator

logger = logging.getLogger(__name__)


class ConfigFileCommandEntry(BaseModel):
    name: str = Field(..., description="The name of the command.")
    description: str = Field(
        ...,
        description="The description of the command. The LLM will use this to determine if the command is relevant to the user's request.",
    )
    prompt: str | None = Field(None, description="The prompt to use if this command is selected. ")
    prompt_file: FilePath | None = Field(None, description="The path to a file containing the prompt to use if this command is selected.")
    allowed_tools: list[str] = Field(..., description="The list of tools that the command can use.")

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
    activation_keywords: list[str] = Field(..., description="The list of activation keywords to enable Gemini for GitHub.")
    globally_allowed_tools: list[str] = Field(..., description="The list of tools that are allowed to be used in all commands.")
    raw_commands: list[ConfigFileCommandEntry] = Field(
        ...,
        description="The list of commands that can be used.",
        validation_alias=AliasChoices("commands"),
    )

    @property
    def commands(self) -> list[ConfigFileCommandEntry]:
        """Get the commands from the raw commands."""

        commands = []

        for cmd in self.raw_commands:
            cmd = cmd.apply_globally_allowed_tools(self.globally_allowed_tools)
            cmd = cmd.apply_tool_restrictions(self.globally_allowed_tools)
            commands.append(cmd)

        return commands

    def get_command_by_name(self, name: str) -> ConfigFileCommandEntry | None:
        """Get a command by name.

        Args:
            name: The name of the command to get.
        """
        return next((cmd for cmd in self.commands if cmd.name == name), None)


class Command(BaseModel):
    name: str = Field(..., description="The name of the command.")
    description: str = Field(
        ...,
        description="The description of the command. The LLM will use this to determine if the command is relevant to the user's request.",
    )
    prompt: str = Field(..., description="The prompt to use if this command is selected. ")
    allowed_tools: list[str] = Field(..., description="The list of tools that the command can use.")

    @classmethod
    def from_config_file_command_entry(
        cls,
        config_file_command_entry: ConfigFileCommandEntry,
        additional_tools: list[str] | None = None,
        tool_restrictions: list[str] | None = None,
    ) -> Self:
        """Create a ConfigCommandEntry instance from a ConfigFileCommandEntry instance."""

        prompt: str

        if config_file_command_entry.prompt:
            prompt = config_file_command_entry.prompt
        elif config_file_command_entry.prompt_file:
            with open(config_file_command_entry.prompt_file) as f:
                prompt = f.read()

        tools = config_file_command_entry.allowed_tools

        if additional_tools:
            tools.extend(additional_tools)

        if tool_restrictions:
            tools = [tool for tool in tools if tool not in tool_restrictions]

        return cls(
            name=config_file_command_entry.name,
            description=config_file_command_entry.description,
            prompt=prompt,
            allowed_tools=tools,
        )


class Config(BaseModel):
    activation_keywords: list[str] = Field(..., description="The list of activation keywords to enable Gemini for GitHub.")
    commands: list[Command] = Field(..., description="The list of commands that can be used.")

    @classmethod
    def from_config_file(cls, config_file: ConfigFile, tool_restrictions: list[str] | None = None) -> Self:
        """Create a Config instance from a ConfigFile instance."""
        return cls(
            activation_keywords=config_file.activation_keywords,
            commands=[
                Command.from_config_file_command_entry(
                    cmd,
                    additional_tools=config_file.globally_allowed_tools,
                    tool_restrictions=tool_restrictions,
                )
                for cmd in config_file.commands
            ],
        )

    def get_command_by_name(self, name: str) -> Command | None:
        """Get a command by name."""
        return next((cmd for cmd in self.commands if cmd.name == name), None)

    def matches_activation_keyword(self, text: str) -> bool:
        """Check if the text matches any of the activation keywords."""
        return any(keyword.lower() in text.lower() for keyword in self.activation_keywords)

    def command_name_to_description_dict(self) -> dict[str, str]:
        """Get a dictionary of command names to descriptions."""
        return {cmd.name: cmd.description for cmd in self.commands}
