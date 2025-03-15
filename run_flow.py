import asyncio
import time

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger


async def run_flow():
    """
    Execute the planning flow with the Manus agent.
    
    This function sets up a planning flow with the Manus agent, prompts the user
    for input, and processes the request through the planning flow. The planning
    flow breaks down complex tasks into manageable steps and executes them
    sequentially.
    
    The function includes error handling for timeouts, keyboard interruptions,
    and general exceptions, with appropriate logging throughout the process.
    """
    # Initialize available agents dictionary with Manus agent
    agents = {
        "manus": Manus(),
    }

    try:
        # Get user input for the task to be performed
        prompt = input("Enter your prompt: ")

        # Validate that the prompt is not empty or just whitespace
        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        # Create a planning flow using the FlowFactory
        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,  # Use planning flow type for structured task execution
            agents=agents,  # Provide the available agents
        )
        logger.warning("Processing your request...")

        try:
            # Track execution time for performance monitoring
            start_time = time.time()
            
            # Execute the flow with a 1-hour timeout to prevent infinite execution
            result = await asyncio.wait_for(
                flow.execute(prompt),
                timeout=3600,  # 60 minute timeout for the entire execution
            )
            
            # Calculate and log the execution time
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
        except asyncio.TimeoutError:
            # Handle timeout case (execution took longer than 1 hour)
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        # Handle user interruption (Ctrl+C) gracefully
        logger.info("Operation cancelled by user.")
    except Exception as e:
        # Handle any other exceptions that might occur
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    # Run the flow function using asyncio event loop
    asyncio.run(run_flow())
