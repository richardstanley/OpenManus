import os

import aiofiles

from app.tool.base import BaseTool


class FileSaver(BaseTool):
    """
    A tool for saving content to files in the OpenManus framework.
    
    This tool provides agents with the ability to write text content to files
    on the local filesystem. It handles directory creation if needed and
    supports both writing new files and appending to existing files.
    
    The tool is particularly useful for saving generated content, code,
    configuration files, or any text-based output that needs to be persisted
    to disk.
    """

    # Tool identification and interface definition
    name: str = "file_saver"
    description: str = """Save content to a local file at a specified path.
Use this tool when you need to save text, code, or generated content to a file on the local filesystem.
The tool accepts content and a file path, and saves the content to that location.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "(required) The content to save to the file.",
            },
            "file_path": {
                "type": "string",
                "description": "(required) The path where the file should be saved, including filename and extension.",
            },
            "mode": {
                "type": "string",
                "description": "(optional) The file opening mode. Default is 'w' for write. Use 'a' for append.",
                "enum": ["w", "a"],
                "default": "w",
            },
        },
        "required": ["content", "file_path"],
    }

    async def execute(self, content: str, file_path: str, mode: str = "w") -> str:
        """
        Save content to a file at the specified path.
        
        This method handles the actual file writing operation, including creating
        any necessary directories in the path if they don't exist. It uses
        asynchronous file I/O for better performance and to avoid blocking
        the event loop during file operations.
        
        The method supports two modes:
        - 'w' (write): Creates a new file or overwrites an existing file
        - 'a' (append): Adds content to the end of an existing file or creates a new file
        
        Args:
            content (str): The text content to save to the file
            file_path (str): The full path where the file should be saved
            mode (str, optional): The file opening mode. Default is 'w' for write.
                                 Use 'a' for append.
        
        Returns:
            str: A message indicating the result of the operation, either success
                 or an error message if the operation failed
        """
        try:
            # Ensure the directory exists
            # Extract the directory path from the full file path
            directory = os.path.dirname(file_path)
            
            # Create the directory and any parent directories if they don't exist
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # Write content to the file using asynchronous I/O
            # This prevents blocking the event loop during file operations
            async with aiofiles.open(file_path, mode, encoding="utf-8") as file:
                await file.write(content)

            # Return a success message with the file path
            return f"Content successfully saved to {file_path}"
        except Exception as e:
            # Handle any errors that occur during the file operation
            # This includes permission errors, disk full errors, etc.
            return f"Error saving file: {str(e)}"
