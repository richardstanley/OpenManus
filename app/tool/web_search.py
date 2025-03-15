import asyncio
from typing import List

from app.config import config
from app.tool.base import BaseTool
from app.tool.search import (
    BaiduSearchEngine,
    DuckDuckGoSearchEngine,
    GoogleSearchEngine,
    WebSearchEngine,
)


class WebSearch(BaseTool):
    """
    A tool for performing web searches and retrieving relevant results.
    
    This tool enables agents to search the web for information using various search engines
    (Google, Baidu, DuckDuckGo). It provides a unified interface for web searches,
    abstracting away the differences between search engines and allowing for configuration-based
    engine selection.
    
    The tool is particularly useful for retrieving up-to-date information that might not be
    available in the agent's training data, researching specific topics, or gathering
    information from the web to answer user queries.
    """

    # Tool identification and interface definition
    name: str = "web_search"
    description: str = """Perform a web search and return a list of relevant links.
Use this tool when you need to find information on the web, get up-to-date data, or research specific topics.
The tool returns a list of URLs that match the search query.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to the search engine.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }
    
    # Dictionary mapping search engine names to their respective implementations
    # This allows for easy switching between different search engines
    _search_engine: dict[str, WebSearchEngine] = {
        "google": GoogleSearchEngine(),
        "baidu": BaiduSearchEngine(),
        "duckduckgo": DuckDuckGoSearchEngine(),
    }

    async def execute(self, query: str, num_results: int = 10) -> List[str]:
        """
        Execute a web search and return a list of URLs.
        
        This method performs the actual web search operation using the configured
        search engine. It runs the search in a separate thread to prevent blocking
        the main event loop, which is important for maintaining responsiveness in
        asynchronous applications.
        
        The method delegates the actual search operation to the appropriate search
        engine implementation based on the configuration.

        Args:
            query (str): The search query to submit to the search engine.
                         This should be a clear, specific search term to get relevant results.
            num_results (int, optional): The number of search results to return.
                                        Default is 10. Higher values provide more
                                        comprehensive results but may take longer.

        Returns:
            List[str]: A list of URLs matching the search query. These URLs can be
                      used for further processing, such as content extraction or
                      providing to the user as reference sources.
        """
        # Run the search in a thread pool to prevent blocking
        # This is important because web searches can take time and we don't want
        # to block the event loop while waiting for results
        loop = asyncio.get_event_loop()
        
        # Get the appropriate search engine based on configuration
        search_engine = self.get_search_engine()
        
        # Execute the search in a thread pool and collect the results
        # Using run_in_executor allows running blocking operations without
        # blocking the event loop
        links = await loop.run_in_executor(
            None,
            lambda: list(search_engine.perform_search(query, num_results=num_results)),
        )

        return links

    def get_search_engine(self) -> WebSearchEngine:
        """
        Determines the search engine to use based on the configuration.
        
        This method reads the search engine configuration from the application
        settings and returns the appropriate search engine implementation.
        If no configuration is provided or the specified engine is not available,
        it falls back to a default engine (Google).
        
        The method abstracts away the details of search engine selection,
        allowing the rest of the code to work with any search engine without
        modification.
        
        Returns:
            WebSearchEngine: An instance of the configured search engine class.
                           This will be one of GoogleSearchEngine, BaiduSearchEngine,
                           or DuckDuckGoSearchEngine.
        """
        # Default to Google if no specific engine is configured
        default_engine = self._search_engine.get("google")
        
        # If search configuration is not provided, use the default engine
        if config.search_config is None:
            return default_engine
        else:
            # Get the configured engine name and convert to lowercase for case-insensitive matching
            engine = config.search_config.engine.lower()
            
            # Return the configured engine or fall back to the default if not found
            return self._search_engine.get(engine, default_engine)
