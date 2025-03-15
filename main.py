import asyncio

from app.agent.manus import Manus
from app.logger import logger


async def main():
    """
    Main entry point for the OpenManus application.
    
    This function initializes the Manus agent, prompts the user for input,
    and processes the request asynchronously. The agent uses various tools
    and LLM capabilities to complete the requested task.
    
    The function handles user interruptions gracefully and provides
    appropriate logging throughout the process.
    """
    # Initialize the Manus agent - a versatile agent with multiple tools
    agent = Manus()
    try:
        # Get user input for the task to be performed
        prompt = input("Enter your prompt: ")
        
        # Validate that the prompt is not empty
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        # Process the user's request using the Manus agent
        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        # Handle user interruption (Ctrl+C) gracefully
        logger.warning("Operation interrupted.")


if __name__ == "__main__":
    # Run the main function using asyncio event loop
    asyncio.run(main())
