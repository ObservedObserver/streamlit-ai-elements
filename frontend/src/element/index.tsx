import { forwardRef } from "react";

// Import Streamlit-specific components from st-ai-elements
export { StPromptInput as PromptInput } from "@/components/st-ai-elements";
export { StConversation as Conversation } from "@/components/st-ai-elements";

interface HelloWorldProps {
    message?: string;
    color?: string;
}

export const HelloWorld = forwardRef<HTMLDivElement, HelloWorldProps>((props, ref) => {
    const { message = "Hello World from Streamlit AI Elements!", color = "#1f77b4" } = props;
    
    return (
        <div ref={ref} style={{ padding: '20px' }}>
            <h1 style={{ color, fontSize: '24px', fontWeight: 'bold' }}>
                {message}
            </h1>
            <p style={{ marginTop: '10px', color: '#666' }}>
                This is a simple example component. Replace this with your own AI elements!
            </p>
        </div>
    );
});
