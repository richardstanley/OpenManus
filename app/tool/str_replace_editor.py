from collections import defaultdict
from pathlib import Path
from typing import Literal, get_args

from app.exceptions import ToolError
from app.tool import BaseTool
from app.tool.base import CLIResult, ToolResult
from app.tool.run import run


# Define the allowed commands as a Literal type for type checking and validation
Command = Literal[
    "view",    # View file or directory contents
    "create",  # Create a new file
    "str_replace",  # Replace text in a file
    "insert",  # Insert text at a specific line
    "undo_edit",  # Undo the last edit
]

# Number of context lines to show before and after edits in snippets
SNIPPET_LINES: int = 4

# Maximum length for responses before truncation
MAX_RESPONSE_LEN: int = 16000

# Message to display when content is truncated
TRUNCATED_MESSAGE: str = "<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>"

# Comprehensive description of the editor tool for the LLM
_STR_REPLACE_EDITOR_DESCRIPTION = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`
"""


def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN):
    """
    Truncate content and append a notice if content exceeds the specified length.
    
    This function helps manage large file contents by truncating them to a 
    reasonable size, preventing excessive token usage and improving readability.
    
    Args:
        content: The string content to potentially truncate
        truncate_after: Maximum length before truncation (None means no truncation)
        
    Returns:
        The original content if it's within length limits, or a truncated
        version with a notice appended if it exceeds the limit
    """
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


class StrReplaceEditor(BaseTool):
    """
    A tool for viewing, creating, and editing files in the OpenManus framework.
    
    This tool provides agents with the ability to interact with the file system,
    view file and directory contents, create new files, and make precise edits
    to existing files. It maintains an edit history to support undoing changes.
    
    The tool is designed to be user-friendly while providing powerful editing
    capabilities, with a focus on exact string replacement and line-based
    insertion to minimize the risk of unintended changes.
    """

    # Tool identification and interface definition
    name: str = "str_replace_editor"
    description: str = _STR_REPLACE_EDITOR_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.",
                "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
                "type": "string",
            },
            "path": {
                "description": "Absolute path to file or directory.",
                "type": "string",
            },
            "file_text": {
                "description": "Required parameter of `create` command, with the content of the file to be created.",
                "type": "string",
            },
            "old_str": {
                "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
                "type": "string",
            },
            "new_str": {
                "description": "Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.",
                "type": "string",
            },
            "insert_line": {
                "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
                "type": "integer",
            },
            "view_range": {
                "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
                "items": {"type": "integer"},
                "type": "array",
            },
        },
        "required": ["command", "path"],
    }

    # Dictionary to store file edit history, keyed by file path
    # Using defaultdict to automatically initialize empty lists for new keys
    _file_history: list = defaultdict(list)

    async def execute(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        **kwargs,
    ) -> str:
        """
        Execute the specified editor command.
        
        This method is the main entry point for all editor operations. It validates
        the command and path, dispatches to the appropriate method based on the
        command, and handles parameter validation.
        
        Args:
            command: The editor command to execute (view, create, str_replace, insert, undo_edit)
            path: Absolute path to the target file or directory
            file_text: Content for file creation (required for 'create')
            view_range: Line range for viewing files [start, end] (optional for 'view')
            old_str: Text to replace (required for 'str_replace')
            new_str: Replacement text (required for 'insert', optional for 'str_replace')
            insert_line: Line number for insertion (required for 'insert')
            **kwargs: Additional parameters (unused)
            
        Returns:
            String representation of the command result
            
        Raises:
            ToolError: If command validation fails or command execution fails
        """
        # Convert string path to Path object for easier manipulation
        _path = Path(path)
        
        # Validate the path and command combination
        self.validate_path(command, _path)
        
        # Dispatch to the appropriate method based on the command
        if command == "view":
            # View file or directory contents
            result = await self.view(_path, view_range)
        elif command == "create":
            # Create a new file
            if file_text is None:
                raise ToolError("Parameter `file_text` is required for command: create")
            self.write_file(_path, file_text)
            self._file_history[_path].append(file_text)
            result = ToolResult(output=f"File created successfully at: {_path}")
        elif command == "str_replace":
            # Replace text in a file
            if old_str is None:
                raise ToolError(
                    "Parameter `old_str` is required for command: str_replace"
                )
            result = self.str_replace(_path, old_str, new_str)
        elif command == "insert":
            # Insert text at a specific line
            if insert_line is None:
                raise ToolError(
                    "Parameter `insert_line` is required for command: insert"
                )
            if new_str is None:
                raise ToolError("Parameter `new_str` is required for command: insert")
            result = self.insert(_path, insert_line, new_str)
        elif command == "undo_edit":
            # Undo the last edit
            result = self.undo_edit(_path)
        else:
            # This should never happen due to the Literal type, but just in case
            raise ToolError(
                f'Unrecognized command {command}. The allowed commands for the {self.name} tool are: {", ".join(get_args(Command))}'
            )
        return str(result)

    def validate_path(self, command: str, path: Path):
        """
        Check that the path/command combination is valid.
        
        This method performs various validations on the provided path and command:
        - Ensures the path is absolute
        - Checks if the path exists (except for 'create' command)
        - Verifies that 'create' is not used on existing files
        - Ensures directory paths are only used with the 'view' command
        
        Args:
            command: The editor command to validate
            path: The Path object to validate
            
        Raises:
            ToolError: If any validation check fails
        """
        # Check if it's an absolute path
        if not path.is_absolute():
            suggested_path = Path("") / path
            raise ToolError(
                f"The path {path} is not an absolute path, it should start with `/`. Maybe you meant {suggested_path}?"
            )
        # Check if path exists (except for 'create' command)
        if not path.exists() and command != "create":
            raise ToolError(
                f"The path {path} does not exist. Please provide a valid path."
            )
        if path.exists() and command == "create":
            raise ToolError(
                f"File already exists at: {path}. Cannot overwrite files using command `create`."
            )
        # Check if the path points to a directory
        if path.is_dir():
            if command != "view":
                raise ToolError(
                    f"The path {path} is a directory and only the `view` command can be used on directories"
                )

    async def view(self, path: Path, view_range: list[int] | None = None):
        """
        Implement the view command for files and directories.
        
        This method handles viewing the contents of files or listing directory contents:
        - For directories: Lists non-hidden files and directories up to 2 levels deep
        - For files: Shows the file content with line numbers, optionally within a specified range
        
        Args:
            path: Path to the file or directory to view
            view_range: Optional line range for viewing files [start, end]
            
        Returns:
            CLIResult containing the command output
            
        Raises:
            ToolError: If view_range is invalid or used with a directory
        """
        # Handle directory viewing
        if path.is_dir():
            if view_range:
                raise ToolError(
                    "The `view_range` parameter is not allowed when `path` points to a directory."
                )

            # Use the find command to list directory contents
            _, stdout, stderr = await run(
                rf"find {path} -maxdepth 2 -not -path '*/\.*'"
            )
            if not stderr:
                stdout = f"Here's the files and directories up to 2 levels deep in {path}, excluding hidden items:\n{stdout}\n"
            return CLIResult(output=stdout, error=stderr)

        # Handle file viewing
        file_content = self.read_file(path)
        init_line = 1
        
        # Handle view range if specified
        if view_range:
            # Validate view_range format
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(
                    "Invalid `view_range`. It should be a list of two integers."
                )
                
            # Split file into lines for range processing
            file_lines = file_content.split("\n")
            n_lines_file = len(file_lines)
            init_line, final_line = view_range
            
            # Validate start line
            if init_line < 1 or init_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its first element `{init_line}` should be within the range of lines of the file: {[1, n_lines_file]}"
                )
                
            # Validate end line
            if final_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be smaller than the number of lines in the file: `{n_lines_file}`"
                )
            if final_line != -1 and final_line < init_line:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be larger or equal than its first `{init_line}`"
                )

            # Extract the specified range of lines
            if final_line == -1:
                file_content = "\n".join(file_lines[init_line - 1 :])
            else:
                file_content = "\n".join(file_lines[init_line - 1 : final_line])

        # Format the output with line numbers
        return CLIResult(
            output=self._make_output(file_content, str(path), init_line=init_line)
        )

    def str_replace(self, path: Path, old_str: str, new_str: str | None):
        """
        Implement the str_replace command to replace text in a file.
        
        This method performs exact string replacement in a file, with safety
        checks to ensure the replacement string appears exactly once in the file.
        It also maintains edit history for undo operations.
        
        Args:
            path: Path to the file to edit
            old_str: The exact string to replace
            new_str: The replacement string (empty string if None)
            
        Returns:
            CLIResult containing the command output with a snippet of the edited section
            
        Raises:
            ToolError: If old_str is not found or appears multiple times in the file
        """
        # Read the file content and normalize tabs
        file_content = self.read_file(path).expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ""

        # Check if old_str is unique in the file
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            # Error if the string is not found
            raise ToolError(
                f"No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}."
            )
        elif occurrences > 1:
            # Error if the string appears multiple times
            file_content_lines = file_content.split("\n")
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f"No replacement was performed. Multiple occurrences of old_str `{old_str}` in lines {lines}. Please ensure it is unique"
            )

        # Replace old_str with new_str
        new_file_content = file_content.replace(old_str, new_str)

        # Write the new content to the file
        self.write_file(path, new_file_content)

        # Save the original content to history for undo
        self._file_history[path].append(file_content)

        # Create a snippet of the edited section for display
        # Calculate the line number where the replacement occurred
        replacement_line = file_content.split(old_str)[0].count("\n")
        # Determine the range of lines to show in the snippet
        start_line = max(0, replacement_line - SNIPPET_LINES)
        end_line = replacement_line + SNIPPET_LINES + new_str.count("\n")
        # Extract the snippet from the new file content
        snippet = "\n".join(new_file_content.split("\n")[start_line : end_line + 1])

        # Prepare the success message with the snippet
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet, f"a snippet of {path}", start_line + 1
        )
        success_msg += "Review the changes and make sure they are as expected. Edit the file again if necessary."

        return CLIResult(output=success_msg)

    def insert(self, path: Path, insert_line: int, new_str: str):
        """
        Implement the insert command to insert text at a specific line.
        
        This method inserts new text after the specified line number in a file.
        It maintains edit history for undo operations and provides a snippet
        of the edited section for review.
        
        Args:
            path: Path to the file to edit
            insert_line: Line number after which to insert the text
            new_str: The text to insert
            
        Returns:
            CLIResult containing the command output with a snippet of the edited section
            
        Raises:
            ToolError: If insert_line is invalid
        """
        # Read the file content and normalize tabs
        file_text = self.read_file(path).expandtabs()
        new_str = new_str.expandtabs()
        
        # Split the file into lines for insertion
        file_text_lines = file_text.split("\n")
        n_lines_file = len(file_text_lines)

        # Validate insert_line
        if insert_line < 0 or insert_line > n_lines_file:
            raise ToolError(
                f"Invalid `insert_line` parameter: {insert_line}. It should be within the range of lines of the file: {[0, n_lines_file]}"
            )

        # Split the new string into lines
        new_str_lines = new_str.split("\n")
        
        # Create the new file content by inserting the new lines
        new_file_text_lines = (
            file_text_lines[:insert_line]  # Lines before insertion point
            + new_str_lines  # New lines to insert
            + file_text_lines[insert_line:]  # Lines after insertion point
        )
        
        # Create a snippet of the edited section for display
        snippet_lines = (
            file_text_lines[max(0, insert_line - SNIPPET_LINES) : insert_line]  # Context before
            + new_str_lines  # Inserted lines
            + file_text_lines[insert_line : insert_line + SNIPPET_LINES]  # Context after
        )

        # Join the lines back into text
        new_file_text = "\n".join(new_file_text_lines)
        snippet = "\n".join(snippet_lines)

        # Write the new content to the file
        self.write_file(path, new_file_text)
        
        # Save the original content to history for undo
        self._file_history[path].append(file_text)

        # Prepare the success message with the snippet
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet,
            "a snippet of the edited file",
            max(1, insert_line - SNIPPET_LINES + 1),
        )
        success_msg += "Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary."
        return CLIResult(output=success_msg)

    def undo_edit(self, path: Path):
        """
        Implement the undo_edit command to revert the last edit.
        
        This method restores the file to its state before the last edit
        by retrieving the previous version from the edit history.
        
        Args:
            path: Path to the file to undo edits for
            
        Returns:
            CLIResult containing the command output with the restored content
            
        Raises:
            ToolError: If no edit history exists for the file
        """
        # Check if there's any edit history for this file
        if not self._file_history[path]:
            raise ToolError(f"No edit history found for {path}.")

        # Pop the last saved version from history
        old_text = self._file_history[path].pop()
        
        # Restore the file to its previous state
        self.write_file(path, old_text)

        # Return success message with the restored content
        return CLIResult(
            output=f"Last edit to {path} undone successfully. {self._make_output(old_text, str(path))}"
        )

    def read_file(self, path: Path):
        """
        Read the content of a file from a given path.
        
        This is a utility method that handles file reading with proper
        error handling and reporting.
        
        Args:
            path: Path to the file to read
            
        Returns:
            The content of the file as a string
            
        Raises:
            ToolError: If the file cannot be read
        """
        try:
            return path.read_text()
        except Exception as e:
            raise ToolError(f"Ran into {e} while trying to read {path}") from None

    def write_file(self, path: Path, file: str):
        """
        Write content to a file at the given path.
        
        This is a utility method that handles file writing with proper
        error handling and reporting.
        
        Args:
            path: Path to the file to write
            file: Content to write to the file
            
        Raises:
            ToolError: If the file cannot be written
        """
        try:
            path.write_text(file)
        except Exception as e:
            raise ToolError(f"Ran into {e} while trying to write to {path}") from None

    def _make_output(
        self,
        file_content: str,
        file_descriptor: str,
        init_line: int = 1,
        expand_tabs: bool = True,
    ):
        """
        Generate formatted output for the CLI based on file content.
        
        This utility method formats file content with line numbers for display,
        similar to the 'cat -n' command. It also handles truncation of large
        content and tab expansion.
        
        Args:
            file_content: The content to format
            file_descriptor: Description of the content source (e.g., file path)
            init_line: Starting line number for the content
            expand_tabs: Whether to expand tabs to spaces
            
        Returns:
            Formatted string with line numbers and content
        """
        # Truncate large content
        file_content = maybe_truncate(file_content)
        
        # Expand tabs if requested
        if expand_tabs:
            file_content = file_content.expandtabs()
            
        # Add line numbers to each line
        file_content = "\n".join(
            [
                f"{i + init_line:6}\t{line}"
                for i, line in enumerate(file_content.split("\n"))
            ]
        )
        
        # Format the final output
        return (
            f"Here's the result of running `cat -n` on {file_descriptor}:\n"
            + file_content
            + "\n"
        )
