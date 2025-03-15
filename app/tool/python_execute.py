import multiprocessing
import sys
from io import StringIO
from typing import Dict

from app.tool.base import BaseTool


class PythonExecute(BaseTool):
    """
    A tool for executing Python code with timeout and safety restrictions.
    
    This tool allows agents to execute arbitrary Python code in a controlled
    environment. It provides isolation through multiprocessing, timeout
    capabilities to prevent infinite loops, and captures stdout to return
    the output of executed code.
    
    The tool is designed with safety in mind, running code in a separate
    process to prevent it from affecting the main application.
    """

    # Tool identification and interface definition
    name: str = "python_execute"
    description: str = "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results."
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
        Execute Python code in a controlled environment.
        
        This internal method runs the provided code string using Python's exec()
        function. It captures standard output by redirecting sys.stdout to a
        StringIO buffer, allowing it to collect print statements and other
        output that would normally go to the console.
        
        Args:
            code: The Python code to execute as a string
            result_dict: A multiprocessing-safe dictionary to store results
            safe_globals: Dictionary of global variables available to the code
            
        Note:
            This method is designed to be run in a separate process via
            multiprocessing to provide isolation from the main application.
        """
        # Save the original stdout to restore it later
        original_stdout = sys.stdout
        try:
            # Redirect stdout to capture print statements
            output_buffer = StringIO()
            sys.stdout = output_buffer
            
            # Execute the code with the provided globals dictionary
            exec(code, safe_globals, safe_globals)
            
            # Store the captured output in the result dictionary
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["success"] = True
        except Exception as e:
            # Capture any exceptions that occur during execution
            result_dict["observation"] = str(e)
            result_dict["success"] = False
        finally:
            # Restore the original stdout
            sys.stdout = original_stdout

    async def execute(
        self,
        code: str,
        timeout: int = 5,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout.
        
        This method is the main entry point for code execution. It creates
        a separate process to run the code, applies a timeout to prevent
        infinite loops or long-running code, and returns the results.
        
        The code is executed with a restricted set of globals to provide
        some level of isolation, though it's not a complete sandbox.
        
        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds (default: 5).
            
        Returns:
            Dict: Contains 'observation' with execution output or error message
                  and 'success' status indicating whether execution completed
                  without errors.
        """
        # Use multiprocessing.Manager to share results between processes
        with multiprocessing.Manager() as manager:
            # Create a shared dictionary to store results
            result = manager.dict({"observation": "", "success": False})
            
            # Prepare a safe globals dictionary for code execution
            # This provides the code with access to Python builtins
            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}
            
            # Create a separate process to run the code
            proc = multiprocessing.Process(
                target=self._run_code, args=(code, result, safe_globals)
            )
            
            # Start the process and wait for it to complete or timeout
            proc.start()
            proc.join(timeout)

            # Handle timeout case
            if proc.is_alive():
                # Terminate the process if it's still running after timeout
                proc.terminate()
                proc.join(1)  # Give it a second to clean up
                return {
                    "observation": f"Execution timeout after {timeout} seconds",
                    "success": False,
                }
                
            # Return the results from the process
            return dict(result)
