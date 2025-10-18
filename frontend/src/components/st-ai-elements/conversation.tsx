import { forwardRef } from "react";
import {
    Conversation as BaseConversation,
    ConversationContent,
    ConversationEmptyState,
    ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
    Message,
    MessageContent,
    MessageAvatar,
} from "@/components/ai-elements/message";
import { MessageSquare } from "lucide-react";

export interface MessageData {
    id: string;
    from: "user" | "assistant";
    content: string;
    avatar?: string;
    name?: string;
}

export interface StConversationProps {
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

export const StConversation = forwardRef<HTMLDivElement, StConversationProps>((props, ref) => {
    const {
        messages = [],
        height = "500px",
        className = "",
        emptyStateIcon,
        emptyStateTitle = "No messages yet",
        emptyStateDescription = "Start a conversation to see messages here",
        showScrollButton = true,
        showAvatars = true,
        messageVariant = "contained",
    } = props;

    const conversationHeight = typeof height === "number" ? `${height}px` : height;

    return (
        <div ref={ref} style={{ width: '100%' }}>
            <BaseConversation 
                className={`relative w-full ${className}`} 
                style={{ height: conversationHeight }}
            >
                <ConversationContent>
                    {messages.length === 0 && (
                        <ConversationEmptyState
                            icon={emptyStateIcon || <MessageSquare className="size-12" />}
                            title={emptyStateTitle}
                            description={emptyStateDescription}
                        />
                    )}
                    {messages.length > 0 && messages.map((message) => (
                        <Message from={message.from} key={message.id}>
                            {showAvatars && message.avatar && (
                                <MessageAvatar 
                                    src={message.avatar} 
                                    name={message.name}
                                />
                            )}
                            <MessageContent variant={messageVariant}>
                                {message.content}
                            </MessageContent>
                        </Message>
                    ))}
                </ConversationContent>
                {showScrollButton && <ConversationScrollButton />}
            </BaseConversation>
        </div>
    );
});

StConversation.displayName = "StConversation";

