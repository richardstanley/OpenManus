class WebSearchEngine(object):
    """
    Abstract base class defining the interface for web search engine implementations.
    
    The WebSearchEngine class serves as a blueprint for concrete search engine
    implementations in the OpenManus framework. It defines a common interface
    that all search engines must implement, enabling the framework to work with
    different search providers (like Google, Baidu, DuckDuckGo) through a unified API.
    
    This abstract class follows the Template Method pattern, where the base class
    defines the interface and derived classes provide specific implementations.
    This approach allows the framework to switch between different search engines
    without changing the code that uses them.
    
    Concrete implementations of this class should handle the specifics of connecting
    to their respective search engines, parsing results, and handling any authentication
    or rate limiting requirements.
    """

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> list[dict]:
        """
        Perform a web search and return a list of search results.
        
        This is the main method that concrete search engine implementations must override.
        It takes a search query and optional parameters, performs the search using the
        specific search engine's API or web interface, and returns the results in a
        standardized format.
        
        The method signature allows for additional positional and keyword arguments
        to support engine-specific features while maintaining a consistent core interface.
        
        Args:
            query (str): The search query to submit to the search engine.
                        This should be the text to search for on the web.
            num_results (int, optional): The maximum number of search results to return.
                                        Default is 10. Implementations should respect this
                                        limit even if the search engine returns more results.
            *args: Additional positional arguments for engine-specific features.
            **kwargs: Additional keyword arguments for engine-specific features.
        
        Returns:
            list[dict]: A list of dictionaries, each representing a search result.
                      The exact structure of these dictionaries may vary by implementation,
                      but they typically include fields like 'title', 'url', and 'snippet'.
        
        Raises:
            NotImplementedError: This method must be implemented by concrete subclasses.
                                Base class raises this error to enforce implementation.
        """
        raise NotImplementedError
