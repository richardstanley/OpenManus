import asyncio
import json
from typing import Optional

from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.dom.service import DomService
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from app.config import config
from app.tool.base import BaseTool, ToolResult


# Maximum length for HTML content to prevent overwhelming responses
MAX_LENGTH = 2000

# Comprehensive description of the browser tool capabilities for the LLM
_BROWSER_DESCRIPTION = """
Interact with a web browser to perform various actions such as navigation, element interaction,
content extraction, and tab management. Supported actions include:
- 'navigate': Go to a specific URL
- 'click': Click an element by index
- 'input_text': Input text into an element
- 'screenshot': Capture a screenshot
- 'get_html': Get page HTML content
- 'get_text': Get text content of the page
- 'read_links': Get all links on the page
- 'execute_js': Execute JavaScript code
- 'scroll': Scroll the page
- 'switch_tab': Switch to a specific tab
- 'new_tab': Open a new tab
- 'close_tab': Close the current tab
- 'refresh': Refresh the current page
"""


class BrowserUseTool(BaseTool):
    """
    A tool for browser automation in the OpenManus framework.
    
    This tool provides agents with the ability to control a web browser,
    enabling web navigation, content extraction, element interaction,
    and other browser-related operations. It serves as a bridge between
    the agent and the browser-use library, which handles the actual
    browser automation.
    
    The tool supports various actions like navigation, clicking elements,
    inputting text, taking screenshots, extracting page content, and
    managing browser tabs.
    """

    # Tool identification and interface definition
    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "click",
                    "input_text",
                    "screenshot",
                    "get_html",
                    "get_text",
                    "execute_js",
                    "scroll",
                    "switch_tab",
                    "new_tab",
                    "close_tab",
                    "refresh",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'navigate' or 'new_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element index for 'click' or 'input_text' actions",
            },
            "text": {"type": "string", "description": "Text for 'input_text' action"},
            "script": {
                "type": "string",
                "description": "JavaScript code for 'execute_js' action",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll' action",
            },
            "tab_id": {
                "type": "integer",
                "description": "Tab ID for 'switch_tab' action",
            },
        },
        "required": ["action"],
        "dependencies": {
            "navigate": ["url"],
            "click": ["index"],
            "input_text": ["index", "text"],
            "execute_js": ["script"],
            "switch_tab": ["tab_id"],
            "new_tab": ["url"],
            "scroll": ["scroll_amount"],
        },
    }

    # Concurrency control to prevent race conditions when multiple operations
    # try to access the browser simultaneously
    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    
    # Browser-related components that are initialized on demand
    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)

    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        """
        Validate the parameters for the browser tool.
        
        This validator ensures that the parameters dictionary is not empty,
        which would make the tool unusable.
        
        Args:
            v: The parameters dictionary to validate
            info: Additional validation context
            
        Returns:
            The validated parameters dictionary
            
        Raises:
            ValueError: If the parameters dictionary is empty
        """
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """
        Ensure browser and context are initialized.
        
        This method lazily initializes the browser and context when needed,
        applying configuration settings from the application config. It handles
        browser creation, context initialization, and configuration of various
        browser settings like proxy, headless mode, etc.
        
        Returns:
            BrowserContext: The initialized browser context
        """
        # Initialize browser if not already done
        if self.browser is None:
            # Default browser configuration
            browser_config_kwargs = {"headless": False, "disable_security": True}

            # Apply configuration from app config if available
            if config.browser_config:
                from browser_use.browser.browser import ProxySettings

                # Handle proxy settings
                if config.browser_config.proxy and config.browser_config.proxy.server:
                    browser_config_kwargs["proxy"] = ProxySettings(
                        server=config.browser_config.proxy.server,
                        username=config.browser_config.proxy.username,
                        password=config.browser_config.proxy.password,
                    )

                # Apply other browser configuration attributes
                browser_attrs = [
                    "headless",
                    "disable_security",
                    "extra_chromium_args",
                    "chrome_instance_path",
                    "wss_url",
                    "cdp_url",
                ]

                for attr in browser_attrs:
                    value = getattr(config.browser_config, attr, None)
                    if value is not None:
                        if not isinstance(value, list) or value:
                            browser_config_kwargs[attr] = value

            # Create the browser instance with the configured settings
            self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

        # Initialize context if not already done
        if self.context is None:
            # Default context configuration
            context_config = BrowserContextConfig()

            # Apply context configuration from app config if available
            if (
                config.browser_config
                and hasattr(config.browser_config, "new_context_config")
                and config.browser_config.new_context_config
            ):
                context_config = config.browser_config.new_context_config

            # Create the browser context and initialize DOM service
            self.context = await self.browser.new_context(context_config)
            self.dom_service = DomService(await self.context.get_current_page())

        return self.context

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
        text: Optional[str] = None,
        script: Optional[str] = None,
        scroll_amount: Optional[int] = None,
        tab_id: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a specified browser action.
        
        This method is the main entry point for browser operations. It handles
        various browser actions like navigation, element interaction, content
        extraction, and tab management. Each action has specific parameter
        requirements and produces a corresponding result.
        
        The method uses a lock to ensure thread safety when multiple operations
        might try to access the browser simultaneously.
        
        Args:
            action: The browser action to perform
            url: URL for navigation or new tab
            index: Element index for click or input actions
            text: Text for input action
            script: JavaScript code for execution
            scroll_amount: Pixels to scroll for scroll action
            tab_id: Tab ID for switch_tab action
            **kwargs: Additional arguments
        
        Returns:
            ToolResult with the action's output or error
        """
        # Use lock to ensure thread safety
        async with self.lock:
            try:
                # Ensure browser is initialized
                context = await self._ensure_browser_initialized()

                # Handle different browser actions
                if action == "navigate":
                    # Navigate to a URL
                    if not url:
                        return ToolResult(error="URL is required for 'navigate' action")
                    await context.navigate_to(url)
                    return ToolResult(output=f"Navigated to {url}")

                elif action == "click":
                    # Click an element by index
                    if index is None:
                        return ToolResult(error="Index is required for 'click' action")
                    element = await context.get_dom_element_by_index(index)
                    if not element:
                        return ToolResult(error=f"Element with index {index} not found")
                    download_path = await context._click_element_node(element)
                    output = f"Clicked element at index {index}"
                    if download_path:
                        output += f" - Downloaded file to {download_path}"
                    return ToolResult(output=output)

                elif action == "input_text":
                    # Input text into an element
                    if index is None or not text:
                        return ToolResult(
                            error="Index and text are required for 'input_text' action"
                        )
                    element = await context.get_dom_element_by_index(index)
                    if not element:
                        return ToolResult(error=f"Element with index {index} not found")
                    await context._input_text_element_node(element, text)
                    return ToolResult(
                        output=f"Input '{text}' into element at index {index}"
                    )

                elif action == "screenshot":
                    # Take a screenshot of the page
                    screenshot = await context.take_screenshot(full_page=True)
                    return ToolResult(
                        output=f"Screenshot captured (base64 length: {len(screenshot)})",
                        system=screenshot,
                    )

                elif action == "get_html":
                    # Get the HTML content of the page
                    html = await context.get_page_html()
                    # Truncate long HTML to prevent overwhelming responses
                    truncated = (
                        html[:MAX_LENGTH] + "..." if len(html) > MAX_LENGTH else html
                    )
                    return ToolResult(output=truncated)

                elif action == "get_text":
                    # Get the text content of the page
                    text = await context.execute_javascript("document.body.innerText")
                    return ToolResult(output=text)

                elif action == "read_links":
                    # Get all links on the page
                    links = await context.execute_javascript(
                        "document.querySelectorAll('a[href]').forEach((elem) => {if (elem.innerText) {console.log(elem.innerText, elem.href)}})"
                    )
                    return ToolResult(output=links)

                elif action == "execute_js":
                    # Execute JavaScript code
                    if not script:
                        return ToolResult(
                            error="Script is required for 'execute_js' action"
                        )
                    result = await context.execute_javascript(script)
                    return ToolResult(output=str(result))

                elif action == "scroll":
                    # Scroll the page
                    if scroll_amount is None:
                        return ToolResult(
                            error="Scroll amount is required for 'scroll' action"
                        )
                    await context.execute_javascript(
                        f"window.scrollBy(0, {scroll_amount});"
                    )
                    direction = "down" if scroll_amount > 0 else "up"
                    return ToolResult(
                        output=f"Scrolled {direction} by {abs(scroll_amount)} pixels"
                    )

                elif action == "switch_tab":
                    # Switch to a specific tab
                    if tab_id is None:
                        return ToolResult(
                            error="Tab ID is required for 'switch_tab' action"
                        )
                    await context.switch_to_tab(tab_id)
                    return ToolResult(output=f"Switched to tab {tab_id}")

                elif action == "new_tab":
                    # Open a new tab
                    if not url:
                        return ToolResult(error="URL is required for 'new_tab' action")
                    await context.create_new_tab(url)
                    return ToolResult(output=f"Opened new tab with URL {url}")

                elif action == "close_tab":
                    # Close the current tab
                    await context.close_current_tab()
                    return ToolResult(output="Closed current tab")

                elif action == "refresh":
                    # Refresh the current page
                    await context.refresh_page()
                    return ToolResult(output="Refreshed current page")

                else:
                    # Handle unknown actions
                    return ToolResult(error=f"Unknown action: {action}")

            except Exception as e:
                # Handle any exceptions that occur during browser operations
                return ToolResult(error=f"Browser action '{action}' failed: {str(e)}")

    async def get_current_state(self) -> ToolResult:
        """
        Get the current browser state as a ToolResult.
        
        This method retrieves the current state of the browser, including
        the current URL, page title, open tabs, and interactive elements.
        This information can be useful for the agent to understand the
        current browser context.
        
        Returns:
            ToolResult with the browser state information or error
        """
        async with self.lock:
            try:
                # Ensure browser is initialized
                context = await self._ensure_browser_initialized()
                
                # Get the current browser state
                state = await context.get_state()
                
                # Extract relevant information from the state
                state_info = {
                    "url": state.url,
                    "title": state.title,
                    "tabs": [tab.model_dump() for tab in state.tabs],
                    "interactive_elements": state.element_tree.clickable_elements_to_string(),
                }
                
                # Return the state information as JSON
                return ToolResult(output=json.dumps(state_info))
            except Exception as e:
                # Handle any exceptions that occur during state retrieval
                return ToolResult(error=f"Failed to get browser state: {str(e)}")

    async def cleanup(self):
        """
        Clean up browser resources.
        
        This method properly closes the browser context and browser instance,
        releasing associated resources. It should be called when the tool
        is no longer needed to prevent resource leaks.
        """
        async with self.lock:
            # Close the browser context if it exists
            if self.context is not None:
                await self.context.close()
                self.context = None
                self.dom_service = None
            
            # Close the browser if it exists
            if self.browser is not None:
                await self.browser.close()
                self.browser = None

    def __del__(self):
        """
        Ensure cleanup when object is destroyed.
        
        This destructor method ensures that browser resources are properly
        cleaned up when the tool instance is garbage collected, preventing
        resource leaks.
        """
        if self.browser is not None or self.context is not None:
            try:
                # Try to run cleanup in the current event loop
                asyncio.run(self.cleanup())
            except RuntimeError:
                # If that fails (e.g., if there's no running event loop),
                # create a new event loop for cleanup
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()
