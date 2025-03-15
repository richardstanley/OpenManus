from typing import Any, List, Optional, Type, Union, get_args, get_origin

from pydantic import BaseModel, Field

from app.tool import BaseTool


class CreateChatCompletion(BaseTool):
    """
    A tool for creating structured chat completions with specific output formatting.
    
    This tool enables agents to generate responses in predefined structured formats,
    supporting various output types including strings, primitive types, lists,
    dictionaries, and Pydantic models. It dynamically builds a JSON schema based
    on the specified response type, allowing the LLM to generate properly formatted
    responses that can be directly converted to the desired Python types.
    
    The tool is particularly useful for ensuring consistent output formats and
    enabling type-safe interactions between the agent and other components of
    the system.
    """

    # Tool identification and interface definition
    name: str = "create_chat_completion"
    description: str = (
        "Creates a structured completion with specified output formatting."
    )

    # Type mapping for JSON schema generation
    type_mapping: dict = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    
    # Configuration properties
    response_type: Optional[Type] = None  # The expected type for the response
    required: List[str] = Field(default_factory=lambda: ["response"])  # Required fields in the response

    def __init__(self, response_type: Optional[Type] = str):
        """
        Initialize with a specific response type.
        
        This constructor allows specifying the expected output type for the
        completion, which determines how the response will be structured and
        validated. By default, it expects a simple string response.
        
        Args:
            response_type: The Python type that the response should be converted to.
                          Can be a primitive type, list, dict, Union, or Pydantic model.
        """
        super().__init__()
        self.response_type = response_type
        self.parameters = self._build_parameters()

    def _build_parameters(self) -> dict:
        """
        Build parameters schema based on response type.
        
        This method dynamically generates a JSON schema that describes the
        expected structure of the response based on the specified response_type.
        The schema is used to guide the LLM in generating properly formatted
        responses.
        
        Returns:
            A dictionary containing the JSON schema for the parameters.
        """
        # Handle simple string responses (most common case)
        if self.response_type == str:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "The response text that should be delivered to the user.",
                    },
                },
                "required": self.required,
            }

        # Handle Pydantic models by using their built-in schema generation
        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            schema = self.response_type.model_json_schema()
            return {
                "type": "object",
                "properties": schema["properties"],
                "required": schema.get("required", self.required),
            }

        # Handle other types (primitives, lists, dicts, unions)
        return self._create_type_schema(self.response_type)

    def _create_type_schema(self, type_hint: Type) -> dict:
        """
        Create a JSON schema for the given type.
        
        This method handles the creation of JSON schemas for various Python types,
        including primitive types, lists, dictionaries, and unions. It uses
        Python's typing module to inspect the structure of complex types.
        
        Args:
            type_hint: The Python type to create a schema for
            
        Returns:
            A dictionary containing the JSON schema for the type
        """
        # Get the origin type and type arguments (for generics like List[str])
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        # Handle primitive types (str, int, bool, etc.)
        if origin is None:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": self.type_mapping.get(type_hint, "string"),
                        "description": f"Response of type {type_hint.__name__}",
                    }
                },
                "required": self.required,
            }

        # Handle List type (e.g., List[str], List[int])
        if origin is list:
            item_type = args[0] if args else Any  # Get the type of list items
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "array",
                        "items": self._get_type_info(item_type),
                    }
                },
                "required": self.required,
            }

        # Handle Dict type (e.g., Dict[str, int])
        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any  # Get the type of dict values
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "additionalProperties": self._get_type_info(value_type),
                    }
                },
                "required": self.required,
            }

        # Handle Union type (e.g., Union[str, int])
        if origin is Union:
            return self._create_union_schema(args)

        # Fallback to default parameters
        return self._build_parameters()

    def _get_type_info(self, type_hint: Type) -> dict:
        """
        Get type information for a single type.
        
        This helper method extracts the JSON schema information for a specific
        type, handling both primitive types and Pydantic models.
        
        Args:
            type_hint: The Python type to get information for
            
        Returns:
            A dictionary containing the JSON schema for the type
        """
        # For Pydantic models, use their built-in schema
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            return type_hint.model_json_schema()

        # For other types, map to JSON schema types
        return {
            "type": self.type_mapping.get(type_hint, "string"),
            "description": f"Value of type {getattr(type_hint, '__name__', 'any')}",
        }

    def _create_union_schema(self, types: tuple) -> dict:
        """
        Create schema for Union types.
        
        This method handles the creation of JSON schemas for Union types,
        which represent values that can be of multiple different types.
        
        Args:
            types: A tuple of types that are part of the Union
            
        Returns:
            A dictionary containing the JSON schema for the Union type
        """
        return {
            "type": "object",
            "properties": {
                "response": {"anyOf": [self._get_type_info(t) for t in types]}
            },
            "required": self.required,
        }

    async def execute(self, required: list | None = None, **kwargs) -> Any:
        """
        Execute the chat completion with type conversion.
        
        This method processes the input parameters and converts the response
        to the specified type. It handles various response formats including
        single values, multiple fields, and structured data.
        
        Args:
            required: List of required field names or None (uses default if None)
            **kwargs: Response data as key-value pairs
            
        Returns:
            The response converted to the specified response_type
        """
        # Use provided required fields or default to self.required
        required = required or self.required

        # Handle case when required is a list of field names
        if isinstance(required, list) and len(required) > 0:
            if len(required) == 1:
                # Single required field - extract just that value
                required_field = required[0]
                result = kwargs.get(required_field, "")
            else:
                # Multiple required fields - return a dictionary of all required fields
                return {field: kwargs.get(field, "") for field in required}
        else:
            # Default to "response" field if required is not specified properly
            required_field = "response"
            result = kwargs.get(required_field, "")

        # Type conversion logic based on the specified response_type
        if self.response_type == str:
            return result  # No conversion needed for strings

        # For Pydantic models, construct an instance with the kwargs
        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            return self.response_type(**kwargs)

        # For lists and dicts, assume the result is already in correct format
        if get_origin(self.response_type) in (list, dict):
            return result

        # For other types, try to convert the result to the specified type
        try:
            return self.response_type(result)
        except (ValueError, TypeError):
            # If conversion fails, return the original result
            return result
