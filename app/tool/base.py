from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    """
    Abstract base class for all tools in the OpenManus framework.
    
    This class defines the interface that all tools must implement,
    combining the abstract base class (ABC) pattern with Pydantic's
    data validation. Tools are the primary way agents interact with
    external systems and perform actions.
    
    Each tool has a name, description, and optional parameters schema
    that define how it can be called by agents.
    """

    name: str  # Unique identifier for the tool
    description: str  # Human-readable description of what the tool does
    parameters: Optional[dict] = None  # JSON Schema for the tool's parameters

    class Config:
        """Pydantic configuration for the BaseTool class."""
        arbitrary_types_allowed = True  # Allow complex types that Pydantic can't validate

    async def __call__(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.
        
        This method allows tools to be called directly as functions,
        providing a convenient shorthand for tool.execute().
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Any: The result of the tool execution
        """
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.
        
        This abstract method must be implemented by all tool subclasses
        to define the tool's actual functionality.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Any: The result of the tool execution
        """
        pass

    def to_param(self) -> Dict:
        """
        Convert tool to function call format.
        
        This method transforms the tool definition into a format
        compatible with the OpenAI function calling API, allowing
        tools to be presented to the LLM as callable functions.
        
        Returns:
            Dict: Tool definition in function call format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult(BaseModel):
    """
    Represents the result of a tool execution.
    
    This class provides a standardized structure for tool results,
    including the output, any errors that occurred, and system
    messages. It includes utility methods for combining and
    manipulating results.
    """

    output: Any = Field(default=None)  # The primary output of the tool
    error: Optional[str] = Field(default=None)  # Error message if the tool failed
    system: Optional[str] = Field(default=None)  # System messages or metadata

    class Config:
        """Pydantic configuration for the ToolResult class."""
        arbitrary_types_allowed = True  # Allow complex types that Pydantic can't validate

    def __bool__(self):
        """
        Determine if the result contains any data.
        
        This method allows ToolResult instances to be used in boolean
        contexts, returning True if any field has a value.
        
        Returns:
            bool: True if any field has a value, False otherwise
        """
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        """
        Combine two ToolResult instances.
        
        This method allows ToolResult instances to be combined using
        the + operator, merging their fields.
        
        Args:
            other: Another ToolResult to combine with this one
            
        Returns:
            ToolResult: A new ToolResult with combined fields
            
        Raises:
            ValueError: If the results cannot be combined
        """
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        """
        Convert the result to a string.
        
        This method provides a string representation of the result,
        prioritizing error messages if present.
        
        Returns:
            str: String representation of the result
        """
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """
        Returns a new ToolResult with the given fields replaced.
        
        This method creates a copy of the result with specified
        fields replaced by new values.
        
        Args:
            **kwargs: Fields to replace and their new values
            
        Returns:
            ToolResult: A new ToolResult with the specified fields replaced
        """
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """
    A specialized ToolResult for command-line interface outputs.
    
    This subclass is used specifically for tools that execute
    command-line operations, providing a consistent way to
    handle and format CLI outputs.
    """
    pass


class ToolFailure(ToolResult):
    """
    A specialized ToolResult that represents a failure.
    
    This subclass is used to explicitly indicate that a tool
    execution has failed, making it easier to detect and
    handle failures in the agent's execution flow.
    """
    pass


class AgentAwareTool:
    """
    A mixin class for tools that need access to the agent.
    
    This class can be combined with BaseTool subclasses to
    create tools that are aware of the agent that is using them,
    allowing for more context-aware tool behavior.
    """
    agent: Optional = None  # Reference to the agent using this tool
