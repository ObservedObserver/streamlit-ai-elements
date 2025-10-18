# StConversation Component

A Streamlit wrapper for the Conversation AI element, providing a beautiful chat interface with automatic scrolling, empty states, and customizable message displays.

## Features

- 📱 Responsive conversation container with auto-scroll
- 💬 Support for user and assistant messages
- 👤 Optional avatar display
- 🎨 Two message variants: contained (default) and flat
- 📜 Auto-scroll button when not at bottom
- ✨ Beautiful empty state
- 🎯 Fully customizable

## Usage

### Python (Streamlit)

```python
import streamlit as st
import streamlit_ai_elements as sae

# Define your messages
messages = [
    {
        "id": "1",
        "from": "user",
        "content": "Hello!",
        "avatar": "https://example.com/user.jpg",
        "name": "User"
    },
    {
        "id": "2",
        "from": "assistant",
        "content": "Hi! How can I help you?",
        "avatar": "https://example.com/bot.jpg",
        "name": "Assistant"
    }
]

# Render the conversation
sae.conversation(
    messages=messages,
    height="600px",
    message_variant="contained",
    show_avatars=True,
    show_scroll_button=True,
    key="my_conversation"
)
```

### React/TypeScript

```tsx
import { StConversation } from "@/components/st-ai-elements";

const messages = [
  {
    id: "1",
    from: "user" as const,
    content: "Hello!",
    avatar: "https://example.com/user.jpg",
    name: "User"
  },
  {
    id: "2",
    from: "assistant" as const,
    content: "Hi! How can I help you?",
    avatar: "https://example.com/bot.jpg",
    name: "Assistant"
  }
];

<StConversation
  messages={messages}
  height="600px"
  messageVariant="contained"
  showAvatars={true}
  showScrollButton={true}
/>
```

## Props

### Python API

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `messages` | `list` | `[]` | List of message dictionaries |
| `height` | `str \| int` | `"500px"` | Height of conversation container |
| `class_name` | `str` | `None` | Additional CSS class name |
| `empty_state_title` | `str` | `"No messages yet"` | Title shown when no messages |
| `empty_state_description` | `str` | `"Start a conversation to see messages here"` | Description for empty state |
| `show_scroll_button` | `bool` | `True` | Show scroll-to-bottom button |
| `show_avatars` | `bool` | `True` | Show message avatars |
| `message_variant` | `str` | `"contained"` | Message style: "contained" or "flat" |
| `key` | `str` | `None` | Unique component key |

### Message Structure

Each message in the `messages` list should have:

```python
{
    "id": str,              # Required: Unique message ID
    "from": str,            # Required: "user" or "assistant"
    "content": str,         # Required: Message text content
    "avatar": str,          # Optional: Avatar image URL
    "name": str             # Optional: Display name
}
```

### TypeScript Props

```typescript
interface MessageData {
    id: string;
    from: "user" | "assistant";
    content: string;
    avatar?: string;
    name?: string;
}

interface StConversationProps {
    messages?: MessageData[];
    height?: string | number;
    className?: string;
    emptyStateIcon?: React.ReactNode;
    emptyStateTitle?: string;
    emptyStateDescription?: string;
    showScrollButton?: boolean;
    showAvatars?: boolean;
    messageVariant?: "contained" | "flat";
}
```

## Examples

### Basic Chat

```python
import streamlit as st
import streamlit_ai_elements as sae

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Display conversation
sae.conversation(
    messages=st.session_state.chat_messages,
    key="chat"
)

# Input for new messages
user_input = sae.prompt_input(key="chat_input")
if user_input:
    # Add user message
    st.session_state.chat_messages.append({
        "id": str(len(st.session_state.chat_messages)),
        "from": "user",
        "content": user_input["text"]
    })
    
    # Add bot response
    st.session_state.chat_messages.append({
        "id": str(len(st.session_state.chat_messages)),
        "from": "assistant",
        "content": "Response to: " + user_input["text"]
    })
    
    st.rerun()
```

### Custom Styling

```python
sae.conversation(
    messages=messages,
    height="800px",
    message_variant="flat",
    show_avatars=False,
    empty_state_title="Ready to chat?",
    empty_state_description="Send a message to get started",
    class_name="my-custom-conversation",
    key="styled_conversation"
)
```

### With Session State

```python
import streamlit as st
import streamlit_ai_elements as sae

# Initialize
if "messages" not in st.session_state:
    st.session_state.messages = []

# Add message function
def add_message(role: str, content: str):
    st.session_state.messages.append({
        "id": str(len(st.session_state.messages) + 1),
        "from": role,
        "content": content,
        "avatar": get_avatar_url(role),
        "name": role.capitalize()
    })

# Display
sae.conversation(
    messages=st.session_state.messages,
    height="600px",
    key="conversation"
)
```

## Message Variants

### Contained (Default)
- User messages: Primary background color, right-aligned
- Assistant messages: Secondary background color, left-aligned
- Both have rounded corners and padding

### Flat
- User messages: Same as contained variant
- Assistant messages: No background, left-aligned, minimal styling
- More space-efficient for long conversations

## Styling

The component uses Tailwind CSS classes and can be customized via the `class_name` prop or by targeting the conversation container in your custom CSS.

## Related Components

- **StPromptInput**: For user input with attachments, voice, and model selection
- **Message**: Raw message component for custom layouts
- **MessageAvatar**: Standalone avatar component

## Dependencies

- `use-stick-to-bottom`: For auto-scroll behavior
- `lucide-react`: For icons
- Message components from `@/components/ai-elements/message`
- Conversation components from `@/components/ai-elements/conversation`

