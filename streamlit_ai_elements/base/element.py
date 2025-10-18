from typing import Optional, Any
from streamlit_ai_elements.utils.declare import declare_component

# Declare the component
_component_func = declare_component("element")

def hello_world(
    message: Optional[str] = None,
    color: Optional[str] = None,
    key: Optional[str] = None
) -> Any:
    """Render a Hello World component.
    
    Args:
        message: Custom message to display (default: "Hello World from Streamlit AI Elements!")
        color: Color of the message text (default: "#1f77b4")
        key: Unique key for the component
    
    Returns:
        Component value
    """
    # Build props dict, only including values that are not None
    props = {}
    if message is not None:
        props["message"] = message
    if color is not None:
        props["color"] = color
    
    # Call the component
    component_value = _component_func(
        component="HelloWorld",
        props=props,
        key=key,
        default=None
    )
    
    return component_value


def prompt_input(
    placeholder: Optional[str] = None,
    show_attachments: bool = True,
    show_voice: bool = True,
    show_search: bool = True,
    show_model_selector: bool = True,
    models: Optional[list] = None,
    default_model: Optional[str] = None,
    key: Optional[str] = None
) -> Any:
    """Render a ChatGPT-style Prompt Input component.
    
    Args:
        placeholder: Placeholder text for the input (default: "What would you like to know?")
        show_attachments: Show attachment upload button (default: True)
        show_voice: Show voice input button (default: True)
        show_search: Show search button (default: True)
        show_model_selector: Show model selector dropdown (default: True)
        models: List of model dicts with 'value' and 'label' keys 
               (default: [{"value": "gpt-4", "label": "GPT-4"}, ...])
        default_model: Default selected model value (default: "gpt-4")
        key: Unique key for the component
    
    Returns:
        Component value containing:
            - text: The input text
            - model: Selected model value
            - timestamp: When the message was submitted
    
    Example:
        >>> result = sae.prompt_input(
        ...     placeholder="Ask me anything...",
        ...     models=[
        ...         {"value": "gpt-4", "label": "GPT-4"},
        ...         {"value": "claude", "label": "Claude"},
        ...         {"value": "gemini", "label": "Gemini"}
        ...     ],
        ...     default_model="gpt-4",
        ...     key="chat_input"
        ... )
        >>> if result:
        ...     st.write(f"User said: {result['text']}")
        ...     st.write(f"Selected model: {result['model']}")
    """
    # Build props dict
    props = {}
    if placeholder is not None:
        props["placeholder"] = placeholder
    props["showAttachments"] = show_attachments
    props["showVoice"] = show_voice
    props["showSearch"] = show_search
    props["showModelSelector"] = show_model_selector
    if models is not None:
        props["models"] = models
    if default_model is not None:
        props["defaultModel"] = default_model
    
    # Call the component
    component_value = _component_func(
        component="PromptInput",
        props=props,
        key=key,
        default=None
    )
    
    return component_value


def conversation(
    messages: Optional[list] = None,
    height: Optional[str | int] = "500px",
    class_name: Optional[str] = None,
    empty_state_title: Optional[str] = None,
    empty_state_description: Optional[str] = None,
    show_scroll_button: bool = True,
    show_avatars: bool = True,
    message_variant: str = "contained",
    key: Optional[str] = None
) -> Any:
    """Render a Conversation component with messages.
    
    Args:
        messages: List of message dicts with 'id', 'from' ('user' or 'assistant'), 
                 'content', and optionally 'avatar' and 'name' fields (default: [])
        height: Height of the conversation container (default: "500px")
        class_name: Additional CSS class name (default: "")
        empty_state_title: Title shown when no messages (default: "No messages yet")
        empty_state_description: Description shown when no messages 
                                 (default: "Start a conversation to see messages here")
        show_scroll_button: Show scroll to bottom button (default: True)
        show_avatars: Show user/assistant avatars (default: True)
        message_variant: Message style - "contained" or "flat" (default: "contained")
        key: Unique key for the component
    
    Returns:
        Component value
    
    Example:
        >>> messages = [
        ...     {
        ...         "id": "1",
        ...         "from": "user",
        ...         "content": "Hello!",
        ...         "avatar": "https://example.com/user.jpg",
        ...         "name": "User"
        ...     },
        ...     {
        ...         "id": "2",
        ...         "from": "assistant",
        ...         "content": "Hi! How can I help you?",
        ...         "avatar": "https://example.com/bot.jpg",
        ...         "name": "Bot"
        ...     }
        ... ]
        >>> sae.conversation(
        ...     messages=messages,
        ...     height="600px",
        ...     message_variant="flat",
        ...     key="chat_conversation"
        ... )
    """
    # Build props dict
    props = {}
    if messages is not None:
        props["messages"] = messages
    else:
        props["messages"] = []
    
    if height is not None:
        props["height"] = height
    if class_name is not None:
        props["className"] = class_name
    if empty_state_title is not None:
        props["emptyStateTitle"] = empty_state_title
    if empty_state_description is not None:
        props["emptyStateDescription"] = empty_state_description
    
    props["showScrollButton"] = show_scroll_button
    props["showAvatars"] = show_avatars
    props["messageVariant"] = message_variant
    
    # Call the component
    component_value = _component_func(
        component="Conversation",
        props=props,
        key=key,
        default=None
    )
    
    return component_value
