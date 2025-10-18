import { forwardRef, useCallback, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import {
    PromptInput as BasePromptInput,
    PromptInputBody,
    PromptInputTextarea,
    PromptInputFooter,
    PromptInputAttachments,
    PromptInputAttachment,
    PromptInputTools,
    PromptInputSubmit,
    PromptInputButton,
    PromptInputActionMenu,
    PromptInputActionMenuTrigger,
    PromptInputActionMenuContent,
    PromptInputActionAddAttachments,
    PromptInputSpeechButton,
    PromptInputModelSelect,
    PromptInputModelSelectTrigger,
    PromptInputModelSelectContent,
    PromptInputModelSelectItem,
    PromptInputModelSelectValue,
} from "@/components/ai-elements/prompt-input";
import { GlobeIcon } from "lucide-react";

export interface StPromptInputProps {
    placeholder?: string;
    showAttachments?: boolean;
    showVoice?: boolean;
    showSearch?: boolean;
    showModelSelector?: boolean;
    models?: Array<{ value: string; label: string }>;
    defaultModel?: string;
}

export const StPromptInput = forwardRef<HTMLDivElement, StPromptInputProps>((props, ref) => {
    const {
        placeholder = "What would you like to know?",
        showAttachments = true,
        showVoice = true,
        showSearch = true,
        showModelSelector = true,
        models = [
            { value: "gpt-4", label: "GPT-4" },
            { value: "gpt-3.5", label: "GPT-3.5" },
            { value: "claude", label: "Claude" },
        ],
        defaultModel = "gpt-4",
    } = props;

    const [inputValue, setInputValue] = useState("");
    const [selectedModel, setSelectedModel] = useState(defaultModel);

    const handleSubmit = useCallback(() => {
        // Send the message back to Streamlit
        Streamlit.setComponentValue({
            text: inputValue,
            model: selectedModel,
            timestamp: Date.now(),
        });
        setInputValue(""); // Clear input after submit
    }, [inputValue, selectedModel]);

    return (
        <div ref={ref} style={{ width: '100%', maxWidth: '48rem', margin: '0 auto', padding: '1rem 0' }}>
            <BasePromptInput onSubmit={handleSubmit} className="rounded-3xl shadow-sm">
                <PromptInputBody>
                    {showAttachments && (
                        <PromptInputAttachments>
                            {(attachment) => (
                                <PromptInputAttachment data={attachment} />
                            )}
                        </PromptInputAttachments>
                    )}
                    <PromptInputTextarea 
                        placeholder={placeholder}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                    />
                </PromptInputBody>
                <PromptInputFooter>
                    <PromptInputTools>
                        {showAttachments && (
                            <PromptInputActionMenu>
                                <PromptInputActionMenuTrigger />
                                <PromptInputActionMenuContent>
                                    <PromptInputActionAddAttachments />
                                </PromptInputActionMenuContent>
                            </PromptInputActionMenu>
                        )}
                        
                        {showVoice && <PromptInputSpeechButton />}
                        
                        {showSearch && (
                            <PromptInputButton>
                                <GlobeIcon size={16} />
                                <span>Search</span>
                            </PromptInputButton>
                        )}
                        
                        {showModelSelector && (
                            <PromptInputModelSelect 
                                onValueChange={setSelectedModel} 
                                value={selectedModel}
                            >
                                <PromptInputModelSelectTrigger>
                                    <PromptInputModelSelectValue />
                                </PromptInputModelSelectTrigger>
                                <PromptInputModelSelectContent>
                                    {models.map((model) => (
                                        <PromptInputModelSelectItem key={model.value} value={model.value}>
                                            {model.label}
                                        </PromptInputModelSelectItem>
                                    ))}
                                </PromptInputModelSelectContent>
                            </PromptInputModelSelect>
                        )}
                    </PromptInputTools>
                    <PromptInputSubmit
                        disabled={!inputValue.trim()}
                    />
                </PromptInputFooter>
            </BasePromptInput>
        </div>
    );
});

StPromptInput.displayName = "StPromptInput";

