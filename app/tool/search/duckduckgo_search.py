from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    """
    Concrete implementation of WebSearchEngine that uses DuckDuckGo as the search provider.
    
    This class implements the WebSearchEngine interface to provide DuckDuckGo search
    functionality to the OpenManus framework. It leverages the 'duckduckgo_search'
    Python package to perform searches against DuckDuckGo's search engine.
    
    DuckDuckGo is known for its privacy-focused approach to web search, not tracking
    users or personalizing search results based on user history. This makes it a good
    alternative to Google for users concerned about privacy or who want more neutral
    search results.
    
    The implementation delegates the actual search functionality to the DDGS class
    from the third-party library, while conforming to the common interface defined
    by the WebSearchEngine base class.
    """

    async def perform_search(self, query, num_results=10, *args, **kwargs):
        """
        Perform a web search using DuckDuckGo and return the results.
        
        This method implements the abstract method defined in the WebSearchEngine
        base class. It uses the 'duckduckgo_search' Python package's DDGS class
        to execute the search query against DuckDuckGo's search engine and retrieve
        the results.
        
        Note that unlike the GoogleSearchEngine implementation, this method is
        defined as asynchronous (using 'async'), although it appears to call a
        synchronous method (DDGS.text). This may be an implementation inconsistency
        that should be addressed, either by making the method synchronous or by
        properly awaiting an asynchronous call.
        
        Args:
            query (str): The search query to submit to DuckDuckGo.
            num_results (int, optional): The maximum number of search results to return.
                                        Default is 10.
            *args: Additional positional arguments (passed to the text function).
            **kwargs: Additional keyword arguments (passed to the text function).
        
        Returns:
            list: A list of search results from DuckDuckGo. The exact format depends
                 on what DDGS.text returns, which is likely to be more structured than
                 just URLs, potentially including titles, descriptions, and other metadata.
        
        Note:
            The 'duckduckgo_search' package may have rate limiting or other restrictions
            imposed by DuckDuckGo. Production use should consider these limitations and
            potentially implement caching or other strategies to avoid issues.
        """
        # Delegate to the 'text' method of the DDGS class from the duckduckgo_search package
        # This method performs a text search and returns the results
        return DDGS.text(query, num_results=num_results)
