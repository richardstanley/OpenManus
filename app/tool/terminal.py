import asyncio
import os
import shlex
from typing import Optional

from app.tool.base import BaseTool, CLIResult


class Terminal(BaseTool):
    """
    A tool for executing terminal commands in the OpenManus framework.
    
    This tool provides agents with the ability to execute shell commands on the
    host system, enabling interaction with the operating system, file manipulation,
    running external programs, and other system-level operations.
    
    The tool maintains state between commands (such as current working directory)
    and implements safety measures to prevent execution of potentially harmful
    commands. It also handles special commands like 'cd' internally to maintain
    proper context.
    """

    # Tool identification and interface definition
    name: str = "execute_command"
    description: str = """Request to execute a CLI command on the system.
Use this when you need to perform system operations or run specific commands to accomplish any step in the user's task.
You must tailor your command to the user's system and provide a clear explanation of what the command does.
Prefer to execute complex CLI commands over creating executable scripts, as they are more flexible and easier to run.
Commands will be executed in the current working directory.
Note: You MUST append a `sleep 0.05` to the end of the command for commands that will complete in under 50ms, as this will circumvent a known issue with the terminal tool where it will sometimes not return the output when the command completes too quickly.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "(required) The CLI command to execute. This should be valid for the current operating system. Ensure the command is properly formatted and does not contain any harmful instructions.",
            }
        },
        "required": ["command"],
    }
    
    # State variables for the terminal tool
    process: Optional[asyncio.subprocess.Process] = None  # Current subprocess if active
    current_path: str = os.getcwd()  # Tracks the current working directory
    lock: asyncio.Lock = asyncio.Lock()  # Ensures thread safety for command execution

    async def execute(self, command: str) -> CLIResult:
        """
        Execute a terminal command asynchronously with persistent context.
        
        This method is the main entry point for command execution. It handles
        multiple commands separated by '&', maintains the current working
        directory context, and properly captures command output and errors.
        
        Special commands like 'cd' are handled internally to maintain state
        between command executions.
        
        Args:
            command (str): The terminal command to execute.
            
        Returns:
            CLIResult: Contains the standard output and error from the command execution.
        """
        # Split the command by & to handle multiple commands
        commands = [cmd.strip() for cmd in command.split("&") if cmd.strip()]
        final_output = CLIResult(output="", error="")

        # Execute each command sequentially
        for cmd in commands:
            # Sanitize the command for safety
            sanitized_command = self._sanitize_command(cmd)

            # Handle 'cd' command internally to maintain directory context
            if sanitized_command.lstrip().startswith("cd "):
                result = await self._handle_cd_command(sanitized_command)
            else:
                # Use lock to ensure thread safety during command execution
                async with self.lock:
                    try:
                        # Create a subprocess to execute the command
                        self.process = await asyncio.create_subprocess_shell(
                            sanitized_command,
                            stdout=asyncio.subprocess.PIPE,  # Capture standard output
                            stderr=asyncio.subprocess.PIPE,  # Capture error output
                            cwd=self.current_path,  # Use the current working directory
                        )
                        # Wait for the command to complete and get output
                        stdout, stderr = await self.process.communicate()
                        result = CLIResult(
                            output=stdout.decode().strip(),  # Convert bytes to string and trim whitespace
                            error=stderr.decode().strip(),
                        )
                    except Exception as e:
                        # Handle any exceptions during command execution
                        result = CLIResult(output="", error=str(e))
                    finally:
                        # Clear the process reference
                        self.process = None

            # Combine outputs from multiple commands
            if result.output:
                final_output.output += (
                    (result.output + "\n") if final_output.output else result.output
                )
            if result.error:
                final_output.error += (
                    (result.error + "\n") if final_output.error else result.error
                )

        # Remove trailing newlines from the final output
        final_output.output = final_output.output.rstrip()
        final_output.error = final_output.error.rstrip()
        return final_output

    async def execute_in_env(self, env_name: str, command: str) -> CLIResult:
        """
        Execute a terminal command asynchronously within a specified Conda environment.
        
        This method provides a convenient way to run commands in a specific
        Conda environment without having to manually activate and deactivate
        the environment. It uses 'conda run' to execute the command in the
        specified environment.
        
        Args:
            env_name (str): The name of the Conda environment.
            command (str): The terminal command to execute within the environment.
            
        Returns:
            CLIResult: Contains the standard output and error from the command execution.
        """
        # Sanitize the command for safety
        sanitized_command = self._sanitize_command(command)

        # Construct the command to run within the Conda environment
        # Using 'conda run -n env_name command' to execute without activating
        # shlex.quote ensures the environment name is properly escaped
        conda_command = f"conda run -n {shlex.quote(env_name)} {sanitized_command}"

        # Execute the conda command using the standard execute method
        return await self.execute(conda_command)

    async def _handle_cd_command(self, command: str) -> CLIResult:
        """
        Handle 'cd' commands to change the current working directory.
        
        This internal method processes 'cd' commands specially since they
        need to affect the tool's state (current_path) rather than just
        executing in a subprocess. It supports absolute paths, relative paths,
        and the home directory shorthand (~).
        
        Args:
            command (str): The 'cd' command to process.
            
        Returns:
            CLIResult: The result of the 'cd' command, including success or error messages.
        """
        try:
            # Parse the command into parts using shlex to handle quoted paths correctly
            parts = shlex.split(command)
            
            # Handle 'cd' with no arguments (go to home directory)
            if len(parts) < 2:
                new_path = os.path.expanduser("~")
            else:
                # Expand user directory if path starts with ~
                new_path = os.path.expanduser(parts[1])

            # Handle relative paths by joining with current directory
            if not os.path.isabs(new_path):
                new_path = os.path.join(self.current_path, new_path)

            # Normalize the path (resolve .. and . components)
            new_path = os.path.abspath(new_path)

            # Verify the directory exists before changing to it
            if os.path.isdir(new_path):
                self.current_path = new_path
                return CLIResult(
                    output=f"Changed directory to {self.current_path}", error=""
                )
            else:
                return CLIResult(output="", error=f"No such directory: {new_path}")
        except Exception as e:
            # Handle any exceptions during directory change
            return CLIResult(output="", error=str(e))

    @staticmethod
    def _sanitize_command(command: str) -> str:
        """
        Sanitize the command for safe execution.
        
        This method implements basic security checks to prevent execution of
        potentially harmful commands. It checks for dangerous commands like
        'rm', 'sudo', etc., and raises an error if they are detected.
        
        Note: This is a basic security measure and not a comprehensive solution.
        More sophisticated security measures would be needed for a production system.
        
        Args:
            command (str): The command to sanitize.
            
        Returns:
            str: The sanitized command if it passes security checks.
            
        Raises:
            ValueError: If the command contains restricted operations.
        """
        # List of potentially dangerous commands to restrict
        dangerous_commands = ["rm", "sudo", "shutdown", "reboot"]
        try:
            # Parse the command into parts using shlex
            parts = shlex.split(command)
            # Check if any part matches a dangerous command
            if any(cmd in dangerous_commands for cmd in parts):
                raise ValueError("Use of dangerous commands is restricted.")
        except Exception:
            # If shlex.split fails, fall back to basic string comparison
            if any(cmd in command for cmd in dangerous_commands):
                raise ValueError("Use of dangerous commands is restricted.")

        # Return the command if it passes security checks
        # Additional sanitization logic could be added here
        return command

    async def close(self):
        """
        Close the persistent shell process if it exists.
        
        This method ensures proper cleanup of any running subprocess,
        first trying to terminate it gracefully and then forcibly killing
        it if necessary. It's important for resource management and
        preventing orphaned processes.
        """
        async with self.lock:
            if self.process:
                # Try to terminate the process gracefully
                self.process.terminate()
                try:
                    # Wait for the process to exit with a timeout
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    # If the process doesn't exit in time, kill it forcibly
                    self.process.kill()
                    await self.process.wait()
                finally:
                    # Clear the process reference
                    self.process = None

    async def __aenter__(self):
        """
        Enter the asynchronous context manager.
        
        This method enables the Terminal tool to be used as an async context
        manager with the 'async with' statement, providing a clean way to
        ensure resources are properly managed.
        
        Returns:
            Terminal: The Terminal instance.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the asynchronous context manager and close the process.
        
        This method is called when exiting an 'async with' block, ensuring
        that any running processes are properly cleaned up, even if an
        exception occurs within the block.
        
        Args:
            exc_type: The exception type if an exception was raised, else None.
            exc_val: The exception value if an exception was raised, else None.
            exc_tb: The traceback if an exception was raised, else None.
        """
        await self.close()
