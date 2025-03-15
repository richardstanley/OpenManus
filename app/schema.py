from enum import Enum
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class Role(str, Enum):
    """
    Enumeration of possible message roles in a conversation.
    
    These roles define the source and purpose of messages in the conversation:
    - SYSTEM: Instructions or context provided by the system
    - USER: Input from the user
    - ASSISTANT: Responses from the AI assistant
    - TOOL: Output from tool executions
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# Create a tuple of role values for type checking and validation
ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]  # type: ignore


class ToolChoice(str, Enum):
    """
    Enumeration of tool selection strategies for the LLM.
    
    These options control how tools are selected during execution:
    - NONE: No tools should be used
    - AUTO: The model can decide whether to use tools
    - REQUIRED: The model must use tools
    """

    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


# Create a tuple of tool choice values for type checking and validation
TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]  # type: ignore


class AgentState(str, Enum):
    """
    Enumeration of possible agent execution states.
    
    These states track the current execution status of an agent:
    - IDLE: Agent is initialized but not actively processing
    - RUNNING: Agent is actively processing a request
    - FINISHED: Agent has completed its task successfully
    - ERROR: Agent encountered an error during execution
    """

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class Function(BaseModel):
    """
    Represents a function that can be called by a tool.
    
    This model defines the structure of a function call with:
    - name: The name of the function to call
    - arguments: The arguments to pass to the function (as a JSON string)
    """

    name: str  # Name of the function to call
    arguments: str  # Arguments as a JSON string


class ToolCall(BaseModel):
    """
    Represents a tool/function call in a message.
    
    This model defines the structure of a tool call with:
    - id: Unique identifier for the tool call
    - type: Type of the tool call (default: "function")
    - function: The function to call
    """

    id: str  # Unique identifier for this tool call
    type: str = "function"  # Type of tool call, currently only "function" is supported
    function: Function  # The function to call


class Message(BaseModel):
    """
    Represents a chat message in the conversation.
    
    This model defines the structure of messages exchanged between the user,
    assistant, system, and tools. It includes support for regular content
    messages as well as tool calls and tool responses.
    """

    role: ROLE_TYPE = Field(...)  # type: ignore  # Role of the message sender (required)
    content: Optional[str] = Field(default=None)  # Text content of the message
    tool_calls: Optional[List[ToolCall]] = Field(default=None)  # Tool calls in the message
    name: Optional[str] = Field(default=None)  # Name of the tool (for tool messages)
    tool_call_id: Optional[str] = Field(default=None)  # ID of the tool call being responded to

    def __add__(self, other) -> List["Message"]:
        """
        Support for Message + list or Message + Message operations.
        
        This operator overloading allows for convenient message combination:
        - Message + list: Prepends the message to the list
        - Message + Message: Creates a list with both messages
        
        Returns:
            List[Message]: A list containing the combined messages
        """
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """
        Support for list + Message operations.
        
        This operator overloading allows for convenient message combination:
        - list + Message: Appends the message to the list
        
        Returns:
            List[Message]: A list containing the combined messages
        """
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """
        Convert message to dictionary format.
        
        This method transforms the Message object into a dictionary format
        suitable for API requests and serialization, including only the
        non-None fields.
        
        Returns:
            dict: Dictionary representation of the message
        """
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.dict() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        return message

    @classmethod
    def user_message(cls, content: str) -> "Message":
        """
        Create a user message.
        
        Factory method to create a message with the USER role.
        
        Args:
            content: The text content of the message
            
        Returns:
            Message: A new message with the USER role
        """
        return cls(role=Role.USER, content=content)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """
        Create a system message.
        
        Factory method to create a message with the SYSTEM role.
        
        Args:
            content: The text content of the message
            
        Returns:
            Message: A new message with the SYSTEM role
        """
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(cls, content: Optional[str] = None) -> "Message":
        """
        Create an assistant message.
        
        Factory method to create a message with the ASSISTANT role.
        
        Args:
            content: The text content of the message (optional)
            
        Returns:
            Message: A new message with the ASSISTANT role
        """
        return cls(role=Role.ASSISTANT, content=content)

    @classmethod
    def tool_message(cls, content: str, name, tool_call_id: str) -> "Message":
        """
        Create a tool message.
        
        Factory method to create a message with the TOOL role,
        representing the output from a tool execution.
        
        Args:
            content: The text content of the message
            name: The name of the tool
            tool_call_id: The ID of the tool call being responded to
            
        Returns:
            Message: A new message with the TOOL role
        """
        return cls(
            role=Role.TOOL, content=content, name=name, tool_call_id=tool_call_id
        )

    @classmethod
    def from_tool_calls(
        cls, tool_calls: List[Any], content: Union[str, List[str]] = "", **kwargs
    ):
        """
        Create an assistant message with tool calls.
        
        Factory method to create a message with the ASSISTANT role
        that includes tool calls, typically used when the assistant
        wants to execute one or more tools.
        
        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
            **kwargs: Additional message parameters
            
        Returns:
            Message: A new message with the ASSISTANT role and tool calls
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role=Role.ASSISTANT, content=content, tool_calls=formatted_calls, **kwargs
        )


class Memory(BaseModel):
    """
    Manages the conversation history for an agent.
    
    This class stores and manages a list of messages that represent
    the conversation history, providing methods to add, retrieve,
    and manipulate messages.
    """

    messages: List[Message] = Field(default_factory=list)  # List of messages in the conversation
    max_messages: int = Field(default=100)  # Maximum number of messages to store

    def add_message(self, message: Message) -> None:
        """
        Add a single message to memory.
        
        This method appends a message to the conversation history
        and enforces the maximum message limit.
        
        Args:
            message: The message to add
        """
        self.messages.append(message)
        # Enforce message limit by keeping only the most recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: List[Message]) -> None:
        """
        Add multiple messages to memory.
        
        This method extends the conversation history with a list of messages.
        
        Args:
            messages: The list of messages to add
        """
        self.messages.extend(messages)

    def clear(self) -> None:
        """
        Clear all messages from memory.
        
        This method removes all messages from the conversation history.
        """
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """
        Get the n most recent messages.
        
        This method retrieves the specified number of most recent messages
        from the conversation history.
        
        Args:
            n: The number of recent messages to retrieve
            
        Returns:
            List[Message]: The n most recent messages
        """
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """
        Convert all messages to a list of dictionaries.
        
        This method transforms all messages in the conversation history
        into a list of dictionaries suitable for API requests and serialization.
        
        Returns:
            List[dict]: List of dictionary representations of the messages
        """
        return [msg.to_dict() for msg in self.messages]
