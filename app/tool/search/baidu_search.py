from baidusearch.baidusearch import search

from app.tool.search.base import WebSearchEngine


class BaiduSearchEngine(WebSearchEngine):
    """
    Concrete implementation of WebSearchEngine that uses Baidu as the search provider.
    
    This class implements the WebSearchEngine interface to provide Baidu search
    functionality to the OpenManus framework. It leverages the 'baidusearch' Python
    package to perform searches against Baidu's search engine.
    
    Baidu is the dominant search engine in China and provides excellent coverage
    of Chinese-language content and regional information. Including this search
    engine option enables the framework to better support multilingual and
    international use cases, particularly for Chinese users or for queries
    related to Chinese content.
    
    Like the other search engine implementations, this class follows a minimalist
    approach, delegating the actual search functionality to a specialized third-party
    library while conforming to the common interface defined by the WebSearchEngine
    base class.
    """

    def perform_search(self, query, num_results=10, *args, **kwargs):
        """
        Perform a web search using Baidu and return the results.
        
        This method implements the abstract method defined in the WebSearchEngine
        base class. It uses the 'search' function from the 'baidusearch' Python
        package to execute the search query against Baidu's search engine and
        retrieve the results.
        
        The implementation is intentionally simple, delegating most of the complexity
        to the underlying library while ensuring the method signature matches the
        interface defined by the base class.
        
        Args:
            query (str): The search query to submit to Baidu. For best results with
                        Chinese content, queries in Chinese characters are recommended.
            num_results (int, optional): The maximum number of search results to return.
                                        Default is 10.
            *args: Additional positional arguments (passed to the search function).
            **kwargs: Additional keyword arguments (passed to the search function).
        
        Returns:
            list: A list of search results from Baidu. The exact format depends on
                 what the 'baidusearch' package's search function returns, which may
                 include URLs and potentially additional metadata.
        
        Note:
            The 'baidusearch' package may have rate limiting or other restrictions
            imposed by Baidu. Additionally, Baidu's search results may be subject to
            regional restrictions and content filtering policies applicable in China.
            Production use should consider these limitations.
        """
        # Delegate to the 'search' function from the baidusearch package
        # This function performs the search against Baidu and returns the results
        return search(query, num_results=num_results)
