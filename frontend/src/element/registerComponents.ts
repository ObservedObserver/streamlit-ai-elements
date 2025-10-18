// Component registry for Streamlit AI Elements
// Add your custom React components here

import { HelloWorld, PromptInput, Conversation } from "./index";

export const ComponentCollection = {
    HelloWorld,
    PromptInput,
    Conversation,
    // Add more components here as you build them
    // Example: 'MyCustomComponent': MyCustomComponent,
} as const;

export type ComponentName = keyof typeof ComponentCollection;
