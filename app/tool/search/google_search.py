from googlesearch import search

from app.tool.search.base import WebSearchEngine


class GoogleSearchEngine(WebSearchEngine):
    """
    Concrete implementation of WebSearchEngine that uses Google as the search provider.
    
    This class implements the WebSearchEngine interface to provide Google search
    functionality to the OpenManus framework. It leverages the 'googlesearch' Python
    package to perform searches against Google's search engine.
    
    The GoogleSearchEngine provides a simple and straightforward implementation
    that delegates the actual search functionality to the third-party library,
    while conforming to the common interface defined by the WebSearchEngine base class.
    
    This implementation allows agents to search the web using Google's powerful
    search capabilities, providing access to a vast amount of up-to-date information
    from across the internet.
    """

    def perform_search(self, query, num_results=10, *args, **kwargs):
        """
        Perform a web search using Google and return the results.
        
        This method implements the abstract method defined in the WebSearchEngine
        base class. It uses the 'googlesearch' Python package to execute the search
        query against Google's search engine and retrieve the results.
        
        The implementation is intentionally simple, delegating most of the complexity
        to the underlying library while ensuring the method signature matches the
        interface defined by the base class.
        
        Args:
            query (str): The search query to submit to Google.
            num_results (int, optional): The maximum number of search results to return.
                                        Default is 10.
            *args: Additional positional arguments (passed to the search function).
            **kwargs: Additional keyword arguments (passed to the search function).
        
        Returns:
            list: A list of URLs matching the search query, as returned by the
                 'googlesearch' package. Note that this differs slightly from the
                 base class documentation, which suggests returning dictionaries.
                 In this implementation, the results are simple URL strings.
        
        Note:
            The 'googlesearch' package may have rate limiting or other restrictions
            imposed by Google. Production use should consider these limitations and
            potentially implement caching or other strategies to avoid issues.
        """
        # Delegate to the 'search' function from the googlesearch package
        # This function returns an iterator of URLs matching the query
        # We convert it to a list before returning to ensure all results are fetched
        return search(query, num_results=num_results)
