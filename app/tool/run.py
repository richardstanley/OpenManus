"""
Utility to run shell commands asynchronously with a timeout.

This module provides a simple, reusable way to execute shell commands
asynchronously with proper timeout handling and output truncation.
It serves as a lower-level utility that can be used by various tools
in the OpenManus framework that need to execute shell commands.
"""

import asyncio


# Constants for output truncation
TRUNCATED_MESSAGE: str = "<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>"
MAX_RESPONSE_LEN: int = 16000  # Maximum length of response before truncation


def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN):
    """
    Truncate content and append a notice if content exceeds the specified length.
    
    This function helps manage large command outputs by truncating them
    to a reasonable size, which is important for:
    1. Preventing excessive token usage when sending outputs to LLMs
    2. Improving readability of large outputs
    3. Ensuring the system remains responsive
    
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


async def run(
    cmd: str,
    timeout: float | None = 120.0,  # seconds
    truncate_after: int | None = MAX_RESPONSE_LEN,
):
    """
    Run a shell command asynchronously with a timeout.
    
    This function executes shell commands in a non-blocking way using asyncio,
    with built-in timeout handling and output truncation. It captures both
    standard output and error streams, and properly handles process termination.
    
    Key features:
    - Asynchronous execution using asyncio
    - Configurable timeout with proper process cleanup
    - Automatic output truncation for large responses
    - Proper encoding of output streams
    - Error handling for timeouts
    
    Args:
        cmd: The shell command to execute
        timeout: Maximum execution time in seconds (None for no timeout)
        truncate_after: Maximum length of output before truncation
        
    Returns:
        A tuple containing:
        - Return code (0 for success, non-zero for errors)
        - Standard output (potentially truncated)
        - Standard error (potentially truncated)
        
    Raises:
        TimeoutError: If the command execution exceeds the specified timeout
    """
    # Create a subprocess to execute the command
    # The shell=True parameter allows execution of complex shell commands
    # Pipes are set up to capture stdout and stderr
    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    try:
        # Wait for the process to complete with timeout
        # process.communicate() returns a tuple of (stdout_data, stderr_data)
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        # Return a tuple of (return_code, stdout, stderr)
        # Note: process.returncode is converted to 0 if it's None or falsy
        # Both stdout and stderr are decoded from bytes to strings and potentially truncated
        return (
            process.returncode or 0,
            maybe_truncate(stdout.decode(), truncate_after=truncate_after),
            maybe_truncate(stderr.decode(), truncate_after=truncate_after),
        )
    except asyncio.TimeoutError as exc:
        # Handle timeout by attempting to kill the process
        try:
            process.kill()  # Force terminate the process
        except ProcessLookupError:
            # This exception occurs if the process has already terminated
            # We can safely ignore it
            pass
        
        # Re-raise as a more specific TimeoutError with a descriptive message
        # This helps callers understand exactly what happened
        raise TimeoutError(
            f"Command '{cmd}' timed out after {timeout} seconds"
        ) from exc
