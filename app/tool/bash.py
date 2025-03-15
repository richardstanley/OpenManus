import asyncio
import os
from typing import Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, CLIResult, ToolResult


# Comprehensive description of the Bash tool for the LLM
_BASH_DESCRIPTION = """Execute a bash command in the terminal.
* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.
* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.
* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.
"""


class _BashSession:
    """
    A session of a bash shell.
    
    This internal class manages a persistent bash process, allowing for
    sequential command execution within the same shell context. It handles
    process creation, command execution, output collection, and proper
    termination of the bash process.
    
    The class uses a sentinel value to detect when command execution is complete
    and implements timeout handling to prevent indefinite waiting.
    """

    _started: bool  # Flag indicating if the session has been started
    _process: asyncio.subprocess.Process  # The underlying bash process

    command: str = "/bin/bash"  # The shell command to execute
    _output_delay: float = 0.2  # Delay between output checks (seconds)
    _timeout: float = 120.0  # Maximum time to wait for command completion (seconds)
    _sentinel: str = "<<exit>>"  # Marker to detect command completion

    def __init__(self):
        """
        Initialize a new bash session.
        
        Sets up the initial state of the session with the session not yet started
        and no timeout condition.
        """
        self._started = False
        self._timed_out = False

    async def start(self):
        """
        Start the bash session.
        
        Creates a new subprocess running a bash shell with pipes for stdin,
        stdout, and stderr. This allows for bidirectional communication with
        the shell process.
        
        If the session is already started, this method does nothing.
        """
        if self._started:
            return

        # Create a new bash process with pipes for communication
        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,  # Create a new process group for proper signal handling
            shell=True,
            bufsize=0,  # Unbuffered I/O for immediate feedback
            stdin=asyncio.subprocess.PIPE,  # Pipe for sending commands
            stdout=asyncio.subprocess.PIPE,  # Pipe for receiving standard output
            stderr=asyncio.subprocess.PIPE,  # Pipe for receiving error output
        )

        self._started = True

    def stop(self):
        """
        Terminate the bash shell.
        
        Sends a termination signal to the bash process, ending the session.
        
        Raises:
            ToolError: If the session has not been started.
        """
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return  # Process already terminated
        self._process.terminate()

    async def run(self, command: str):
        """
        Execute a command in the bash shell.
        
        Sends the command to the bash process, waits for execution to complete,
        and collects the output. Uses a sentinel value to detect when the command
        has finished executing.
        
        Args:
            command: The bash command to execute
            
        Returns:
            CLIResult: The output and any errors from the command execution
            
        Raises:
            ToolError: If the session has timed out or not been started
        """
        # Check if the session is in a valid state
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # Ensure pipes are available
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # Send command to the process with a sentinel to detect completion
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # Read output from the process until the sentinel is found or timeout occurs
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)  # Brief pause between checks
                    # Access the buffer directly to avoid waiting for EOF
                    output = (
                        self._process.stdout._buffer.decode()
                    )  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # Strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            # Mark the session as timed out if it exceeds the timeout
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        # Clean up the output
        if output.endswith("\n"):
            output = output[:-1]

        # Get any error output
        error = (
            self._process.stderr._buffer.decode()
        )  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # Clear the buffers for the next command
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        # Return the command results
        return CLIResult(output=output, error=error)


class Bash(BaseTool):
    """
    A tool for executing bash commands in the OpenManus framework.
    
    This tool provides agents with the ability to execute shell commands,
    enabling interaction with the operating system, file manipulation,
    running external programs, and other system-level operations.
    
    The tool maintains a persistent bash session, allowing for context
    to be preserved between commands (e.g., current directory, environment
    variables, etc.).
    """

    # Tool identification and interface definition
    name: str = "bash"
    description: str = _BASH_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.",
            },
        },
        "required": ["command"],
    }

    # The underlying bash session
    _session: Optional[_BashSession] = None

    async def execute(
        self, command: str | None = None, restart: bool = False, **kwargs
    ) -> CLIResult:
        """
        Execute a bash command.
        
        This method handles the execution of bash commands, managing the
        underlying bash session and handling restarts when necessary.
        
        Args:
            command: The bash command to execute
            restart: Whether to restart the bash session
            **kwargs: Additional parameters (unused)
            
        Returns:
            CLIResult: The output and any errors from the command execution
            
        Raises:
            ToolError: If no command is provided
        """
        # Handle session restart if requested
        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession()
            await self._session.start()

            return ToolResult(system="tool has been restarted.")

        # Create a new session if none exists
        if self._session is None:
            self._session = _BashSession()
            await self._session.start()

        # Execute the command if provided
        if command is not None:
            return await self._session.run(command)

        # Raise an error if no command is provided
        raise ToolError("no command provided.")


# Example usage of the Bash tool
if __name__ == "__main__":
    bash = Bash()
    rst = asyncio.run(bash.execute("ls -l"))
    print(rst)
