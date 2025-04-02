"""
Main entry point for the OpenManus application.
This module initializes and runs the Manus agent, handling user input and cleanup.
"""

import asyncio

from app.agent.manus import Manus
from app.logger import logger


async def main():
    """
    Main async function that runs the Manus agent.
    Handles user input, agent execution, and cleanup.
    """
    # Initialize the Manus agent
    agent = Manus()
    try:
        # Get user input for the task
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        # Process the user's request
        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        # Handle user interruption gracefully
        logger.warning("Operation interrupted.")
    finally:
        # Ensure proper cleanup of agent resources
        await agent.cleanup()


if __name__ == "__main__":
    # Run the main function using asyncio
    asyncio.run(main())
