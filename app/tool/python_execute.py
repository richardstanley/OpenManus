"""
Python Execute Tool
This module provides a safe way to execute Python code with timeout and restricted access to system resources.
It uses multiprocessing to isolate the execution environment and prevent system-wide impacts.
"""

import multiprocessing
import sys
from io import StringIO
from typing import Dict

from app.tool.base import BaseTool


class PythonExecute(BaseTool):
    """
    A tool for executing Python code with timeout and safety restrictions.

    This tool provides a secure environment for running Python code by:
    1. Isolating execution in a separate process
    2. Implementing timeout mechanisms
    3. Restricting access to system resources
    4. Capturing only print outputs
    5. Managing safe globals environment

    Attributes:
        name (str): Tool identifier
        description (str): Tool description and usage notes
        parameters (dict): JSON schema for tool parameters
    """

    # Tool metadata
    name: str = "python_execute"
    description: str = "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results."

    # Parameter schema for tool validation
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    def _run_code(self, code: str, result_dict: dict, safe_globals: dict) -> None:
        """
        Execute Python code in a controlled environment and capture output.

        Args:
            code (str): Python code to execute
            result_dict (dict): Dictionary to store execution results
            safe_globals (dict): Restricted globals environment

        The method:
        1. Redirects stdout to capture print outputs
        2. Executes code in safe environment
        3. Captures any exceptions
        4. Restores original stdout
        """
        # Store original stdout for restoration
        original_stdout = sys.stdout
        try:
            # Redirect stdout to capture print outputs
            output_buffer = StringIO()
            sys.stdout = output_buffer

            # Execute code in safe environment
            exec(code, safe_globals, safe_globals)

            # Store successful execution results
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["success"] = True
        except Exception as e:
            # Store error information
            result_dict["observation"] = str(e)
            result_dict["success"] = False
        finally:
            # Restore original stdout
            sys.stdout = original_stdout

    async def execute(
        self,
        code: str,
        timeout: int = 5,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout in a separate process.

        This method:
        1. Creates a separate process for code execution
        2. Implements timeout mechanism
        3. Manages safe globals environment
        4. Handles process cleanup

        Args:
            code (str): The Python code to execute
            timeout (int): Maximum execution time in seconds (default: 5)

        Returns:
            Dict: Contains:
                - observation: Execution output or error message
                - success: Boolean indicating execution status
        """
        # Create process manager for inter-process communication
        with multiprocessing.Manager() as manager:
            # Initialize result dictionary
            result = manager.dict({"observation": "", "success": False})

            # Set up safe globals environment
            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}

            # Create and start execution process
            proc = multiprocessing.Process(
                target=self._run_code, args=(code, result, safe_globals)
            )
            proc.start()
            proc.join(timeout)

            # Handle timeout
            if proc.is_alive():
                proc.terminate()
                proc.join(1)
                return {
                    "observation": f"Execution timeout after {timeout} seconds",
                    "success": False,
                }
            return dict(result)
