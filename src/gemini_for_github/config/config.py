from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, FilePath, model_validator

from gemini_for_github.shared.logging import BASE_LOGGER

logger = BASE_LOGGER.getChild("config")


class ConfigFileMCPServerEntry(BaseModel):
    """Represents an MCP server entry as defined in the raw configuration file."""

    name: str = Field(..., description="The unique name identifier for the MCP server.")
    command: str = Field(..., description="The executable command used to start the MCP server.")
    args: list[str] = Field(..., description="A list of arguments to be passed to the MCP server command.")
    env: dict[str, str] = Field(..., description="Environment variables to be set for the MCP server's process.")
    disabled: bool = Field(False, description="If True, this MCP server will not be started or used.")


class ConfigFileCommandEntry(BaseModel):
    """Represents a command entry as defined in the raw configuration file."""

    name: str = Field(..., description="The unique name identifier for the command.")
    description: str = Field(
        ...,
        description="A human-readable description of what the command does. This is used by the LLM to select the appropriate command.",
    )
    prompt: str | None = Field(
        None, description="The direct string prompt to be used if this command is selected. Mutually exclusive with prompt_file."
    )
    prompt_file: FilePath | None = Field(
        None, description="The path to a file containing the prompt to be used if this command is selected. Mutually exclusive with prompt."
    )
    allowed_tools: list[str] = Field(default_factory=list, description="A list of tool names that this command is permitted to use.")
    example_flow: str | None = Field(
        None, description="An illustrative example of how this command might be used or the sequence of actions it performs."
    )

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
        """
        Filters the command's allowed tools to include only those also present in the provided `allowed_tools` list.
        This is used to apply a global baseline of permitted tools.

        Args:
            allowed_tools: A list of globally allowed tool names.

        Returns:
            A new ConfigFileCommandEntry instance with the filtered list of allowed_tools.
        """
        intersection = set(self.allowed_tools) & set(allowed_tools)

        logger.debug(f"Applying globally allowed tools to command {self.name}: {intersection}")

        return self.model_copy(update={"allowed_tools": list(intersection)})

    def apply_tool_restrictions(self, only_allow_these_tools: list[str]) -> Self:
        """
        Further restricts the command's allowed tools to only those present in the `only_allow_these_tools` list.
        This is typically used for applying command-specific or runtime restrictions.

        Args:
            only_allow_these_tools: A list of tool names to restrict the command to.

        Returns:
            A new ConfigFileCommandEntry instance with the further restricted list of allowed_tools.
        """
        intersection = set(self.allowed_tools) & set(only_allow_these_tools)

        logger.debug(f"Applying tool restrictions to command {self.name}: {intersection}")

        return self.model_copy(update={"allowed_tools": list(intersection)})


class ConfigFile(BaseModel):
    """Represents the entire structure of the raw YAML configuration file."""

    activation_keywords: list[str] = Field(
        default_factory=list, description="Keywords that, if present at the start of a user's message, will trigger the agent."
    )
    globally_allowed_tools: list[str] = Field(
        default_factory=list, description="A baseline list of tool names permitted for use by any command."
    )
    mcp_servers: list[ConfigFileMCPServerEntry] = Field(
        default_factory=list, description="Definitions for MCP servers to be made available."
    )
    commands: list[ConfigFileCommandEntry] = Field(..., description="Definitions for all available commands.")
    system_prompt: str = Field(..., description="The overarching system prompt guiding the LLM's behavior for all commands.")


class Command(BaseModel):
    """Represents a processed and validated command, ready for use by the application."""

    name: str = Field(..., description="The unique name identifier for the command.")
    description: str = Field(
        ...,
        description="A human-readable description of what the command does. This is used by the LLM to select the appropriate command.",
    )
    prompt: str = Field(..., description="The fully resolved prompt string to be used if this command is selected.")
    allowed_tools: list[str] = Field(
        ..., description="The final list of tool names that this command is permitted to use after all restrictions."
    )
    example_flow: str | None = Field(
        None, description="An illustrative example of how this command might be used or the sequence of actions it performs."
    )

    @classmethod
    def from_config_file_command_entry(
        cls,
        config_file_command_entry: ConfigFileCommandEntry,
        additional_tools: list[str] | None = None,
        tool_restrictions: list[str] | None = None,
    ) -> Self:
        """
        Creates a processed Command instance from a raw ConfigFileCommandEntry.
        This involves resolving the prompt (from string or file) and applying
        global and specific tool restrictions.

        Args:
            config_file_command_entry: The raw command entry from the config file.
            additional_tools: A list of globally allowed tools to be considered.
            tool_restrictions: A list of specific tool restrictions to apply to this command.

        Returns:
            A processed Command instance.
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
    """Represents a processed and validated MCP server configuration, ready for use."""

    name: str = Field(..., description="The unique name identifier for the MCP server.")
    command: str = Field(..., description="The executable command used to start the MCP server.")
    args: list[str] = Field(..., description="A list of arguments to be passed to the MCP server command.")
    env: dict[str, str] = Field(..., description="Environment variables to be set for the MCP server's process.")
    disabled: bool = Field(False, description="If True, this MCP server will not be started or used.")

    @classmethod
    def from_config_file_mcp_server_entry(cls, config_file_mcp_server_entry: ConfigFileMCPServerEntry) -> Self:
        """Creates an MCPServerConfiguration from a raw ConfigFileMCPServerEntry."""
        return cls(**config_file_mcp_server_entry.model_dump())


class Config(BaseModel):
    """
    Represents the fully processed and validated application configuration.
    This object is used throughout the application to access configuration values.
    """

    activation_keywords: list[str] = Field(
        ..., description="Keywords that, if present at the start of a user's message, will trigger the agent."
    )
    commands: list[Command] = Field(..., description="The list of all processed and available commands.")
    system_prompt: str = Field(..., description="The overarching system prompt guiding the LLM's behavior for all commands.")
    mcp_servers: list[MCPServerConfiguration] = Field(..., description="The list of all processed and available MCP server configurations.")

    @classmethod
    def from_config_file(
        cls,
        config_file: ConfigFile,
        tool_restrictions: list[str] | None = None,
        command_restrictions: list[str] | None = None,
        activation_keywords: list[str] | None = None,
    ) -> Self:
        """
        Creates the final, processed Config instance from a raw ConfigFile object
        and any runtime restrictions.

        Args:
            config_file: The raw configuration loaded from the YAML file.
            tool_restrictions: Optional list of tool names to restrict all commands to.
            command_restrictions: Optional list of command names to restrict availability to.
            activation_keywords: Optional list of activation keywords to override those in the config file.

        Returns:
            A processed Config instance.
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
