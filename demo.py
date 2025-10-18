import streamlit as st
import streamlit_ai_elements as sae

st.set_page_config(page_title="Streamlit AI Elements Demo", layout="wide")

st.title("Streamlit AI Elements Demo")

st.markdown("""
This demo showcases the AI Elements components available in Streamlit AI Elements.
Use these components to build powerful AI-powered Streamlit applications!
""")

# Sidebar navigation
demo_option = st.sidebar.radio(
    "Choose a demo:",
    ["Hello World", "Prompt Input", "Conversation"]
)

if demo_option == "Hello World":
    st.header("Hello World Component")
    
    st.markdown("""
    A simple example component to get started with Streamlit AI Elements.
    """)

    # Example 1: Default Hello World
    st.subheader("Example 1: Default Message")
    sae.hello_world()

    st.markdown("---")

    # Example 2: Custom Message
    st.subheader("Example 2: Custom Message")
    sae.hello_world(message="Welcome to Streamlit AI Elements!", color="#ff6b6b")

    st.markdown("---")

    # Example 3: Interactive with user input
    st.subheader("Example 3: Interactive")
    user_message = st.text_input("Enter your custom message:", "Your custom message here")
    user_color = st.color_picker("Pick a color:", "#4CAF50")

    sae.hello_world(message=user_message, color=user_color)

elif demo_option == "Prompt Input":
    st.header("Prompt Input Component")
    
    st.markdown("""
    A ChatGPT-style prompt input component with support for attachments, voice input, 
    search, and model selection. Perfect for building AI chat interfaces!
    """)

    # Example 1: Full-Featured Input
    st.subheader("Example 1: Full-Featured Prompt Input")
    st.markdown("Try typing a message and pressing Enter or clicking the submit button.")
    
    result1 = sae.prompt_input(
        placeholder="What would you like to know?",
        show_attachments=True,
        show_voice=True,
        show_search=True,
        show_model_selector=True,
        models=[
            {"value": "gpt-4", "label": "GPT-4"},
            {"value": "gpt-3.5", "label": "GPT-3.5 Turbo"},
            {"value": "claude-3", "label": "Claude 3"},
            {"value": "gemini-pro", "label": "Gemini Pro"}
        ],
        default_model="gpt-4",
        key="full_prompt"
    )
    
    if result1:
        st.write("**Received:**")
        st.json(result1)

    st.markdown("---")

    # Example 2: Simple Input
    st.subheader("Example 2: Simple Input (No Extra Features)")
    st.markdown("A minimal version with just the text input.")
    
    result2 = sae.prompt_input(
        placeholder="Type your message...",
        show_attachments=False,
        show_voice=False,
        show_search=False,
        show_model_selector=False,
        key="simple_prompt"
    )
    
    if result2:
        st.write("**Received:**")
        st.json(result2)

    st.markdown("---")

    # Example 3: Custom Configuration
    st.subheader("Example 3: Custom Configuration")
    st.markdown("Toggle features on/off and customize the component.")
    
    col1, col2 = st.columns(2)
    with col1:
        custom_placeholder = st.text_input(
            "Placeholder text:",
            "Ask me anything..."
        )
        show_attachments = st.checkbox("Show attachments", value=True)
        show_voice = st.checkbox("Show voice button", value=True)
    
    with col2:
        show_search = st.checkbox("Show search button", value=True)
        show_model_selector = st.checkbox("Show model selector", value=True)
    
    result3 = sae.prompt_input(
        placeholder=custom_placeholder,
        show_attachments=show_attachments,
        show_voice=show_voice,
        show_search=show_search,
        show_model_selector=show_model_selector,
        models=[
            {"value": "gpt-4", "label": "GPT-4"},
            {"value": "claude", "label": "Claude"}
        ],
        default_model="gpt-4",
        key="custom_prompt"
    )
    
    if result3:
        st.success("Message submitted!")
        st.write("**Received:**")
        st.json(result3)

    st.markdown("---")

    # Example 4: Chat Interface
    st.subheader("Example 4: Simple Chat Interface")
    st.markdown("Build a chat interface with model selection.")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("model"):
                st.caption(f"Model: {message['model']}")

    # Chat input
    result4 = sae.prompt_input(
        placeholder="Type your message...",
        models=[
            {"value": "gpt-4", "label": "GPT-4"},
            {"value": "gpt-3.5", "label": "GPT-3.5"},
            {"value": "claude", "label": "Claude"}
        ],
        key="chat_prompt"
    )
    
    if result4 and result4.get("text"):
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user",
            "content": result4["text"],
            "model": result4.get("model", "gpt-4")
        })
        
        # Add assistant response (echo for demo)
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Echo ({result4.get('model', 'gpt-4')}): {result4['text']}",
            "model": result4.get("model", "gpt-4")
        })
        
        # Rerun to show updated chat
        st.rerun()

elif demo_option == "Conversation":
    st.header("Conversation Component")
    
    st.markdown("""
    A beautiful conversation UI component with auto-scrolling, avatars, and message bubbles.
    Perfect for displaying chat history and building chat interfaces!
    """)

    # Initialize conversation messages
    if "conversation_messages" not in st.session_state:
        st.session_state.conversation_messages = [
            {
                "id": "1",
                "from": "user",
                "content": "Hello! Can you help me understand how to use this conversation component?",
                "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix",
                "name": "User"
            },
            {
                "id": "2",
                "from": "assistant",
                "content": "Of course! The conversation component is a beautiful way to display chat messages. It supports user and assistant messages, avatars, and automatically scrolls to show new messages.",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Assistant",
                "name": "Assistant"
            },
            {
                "id": "3",
                "from": "user",
                "content": "That sounds great! What customization options are available?",
                "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix",
                "name": "User"
            },
            {
                "id": "4",
                "from": "assistant",
                "content": "You can customize:\n- Height of the conversation area\n- Message variant (contained or flat style)\n- Show/hide avatars\n- Show/hide scroll-to-bottom button\n- Empty state text and icon\n- Custom CSS classes",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Assistant",
                "name": "Assistant"
            }
        ]

    # Example 1: Default Conversation
    st.subheader("Example 1: Default Conversation")
    st.markdown("A conversation with default settings.")
    
    sae.conversation(
        messages=st.session_state.conversation_messages,
        key="default_conversation"
    )

    st.markdown("---")

    # Example 2: Custom Styled Conversation
    st.subheader("Example 2: Custom Configuration")
    st.markdown("Try different styles and settings.")
    
    col1, col2 = st.columns(2)
    with col1:
        conv_height = st.text_input("Height", value="400px", key="conv_height")
        message_variant = st.selectbox("Message Variant", ["contained", "flat"], key="conv_variant")
    
    with col2:
        show_avatars = st.checkbox("Show Avatars", value=True, key="conv_avatars")
        show_scroll_button = st.checkbox("Show Scroll Button", value=True, key="conv_scroll")
    
    sae.conversation(
        messages=st.session_state.conversation_messages,
        height=conv_height,
        message_variant=message_variant,
        show_avatars=show_avatars,
        show_scroll_button=show_scroll_button,
        key="custom_conversation"
    )

    st.markdown("---")

    # Example 3: Interactive - Add Messages
    st.subheader("Example 3: Interactive Conversation")
    st.markdown("Add messages dynamically to the conversation.")
    
    # Form to add new message
    with st.form("add_message_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            new_message = st.text_area("Message content", key="new_message_text")
        with col2:
            message_from = st.radio("From", ["user", "assistant"], key="new_message_from")
            submit_message = st.form_submit_button("Add Message")
    
    if submit_message and new_message:
        new_msg = {
            "id": str(len(st.session_state.conversation_messages) + 1),
            "from": message_from,
            "content": new_message,
            "avatar": f"https://api.dicebear.com/7.x/{'avataaars' if message_from == 'user' else 'bottts'}/svg?seed={message_from}",
            "name": message_from.capitalize()
        }
        st.session_state.conversation_messages.append(new_msg)
        st.rerun()
    
    # Display the interactive conversation
    sae.conversation(
        messages=st.session_state.conversation_messages,
        height="500px",
        key="interactive_conversation"
    )
    
    # Clear messages button
    if st.button("Clear All Messages"):
        st.session_state.conversation_messages = []
        st.rerun()

    st.markdown("---")

    # Example 4: Full Chat Interface (Conversation + Prompt Input)
    st.subheader("Example 4: Complete Chat Interface")
    st.markdown("Combining Conversation and Prompt Input components for a full chat experience.")
    
    # Initialize full chat messages and last processed timestamp
    if "full_chat_messages" not in st.session_state:
        st.session_state.full_chat_messages = []
    if "last_processed_timestamp" not in st.session_state:
        st.session_state.last_processed_timestamp = None
    
    # Display conversation
    sae.conversation(
        messages=st.session_state.full_chat_messages,
        height="400px",
        empty_state_title="Ready to chat?",
        empty_state_description="Type a message below to start the conversation",
        key="full_chat_conversation"
    )
    
    # Prompt input
    chat_result = sae.prompt_input(
        placeholder="Type your message here...",
        show_model_selector=True,
        models=[
            {"value": "gpt-4", "label": "GPT-4"},
            {"value": "claude", "label": "Claude"},
            {"value": "gemini", "label": "Gemini"}
        ],
        key="full_chat_input"
    )
    
    # Only process if we have a new message (check timestamp to avoid infinite loop)
    if chat_result and chat_result.get("text"):
        current_timestamp = chat_result.get("timestamp")
        if current_timestamp != st.session_state.last_processed_timestamp:
            # Update the last processed timestamp
            st.session_state.last_processed_timestamp = current_timestamp
            
            # Add user message
            st.session_state.full_chat_messages.append({
                "id": str(len(st.session_state.full_chat_messages) + 1),
                "from": "user",
                "content": chat_result["text"],
                "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=User",
                "name": "User"
            })
            
            # Add assistant response (echo for demo)
            st.session_state.full_chat_messages.append({
                "id": str(len(st.session_state.full_chat_messages) + 1),
                "from": "assistant",
                "content": f"Echo from {chat_result.get('model', 'gpt-4')}: {chat_result['text']}",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Bot",
                "name": "Assistant"
            })
            
            st.rerun()
    
    # Show message data
    with st.expander("View Message Data Structure"):
        st.json(st.session_state.full_chat_messages)

st.markdown("---")

st.info("""
**Next Steps:**
1. Explore the components in `frontend/src/components/ai-elements/`
2. Modify components in `frontend/src/element/index.tsx`
3. Add new components to `frontend/src/element/registerComponents.ts`
4. Create Python wrappers in `streamlit_ai_elements/base/element.py`
5. Build amazing AI-powered Streamlit applications!
""")
