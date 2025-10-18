# Streamlit AI Elements Components

This directory contains Streamlit-specific wrappers for AI components.

## Structure

```
st-ai-elements/
├── prompt-input.tsx    # Prompt input with file attachments
├── index.ts            # Exports all components
└── README.md          # This file
```

## How It Works

1. **Base Components**: Located in `@/components/ai-elements/` - these are the pure UI components
2. **Streamlit Wrappers**: Located here - these wrap the base components and handle Streamlit communication

## Adding New Components

1. Create a new file (e.g., `my-component.tsx`)
2. Import the base component from `@/components/ai-elements/`
3. Wrap it with Streamlit communication logic
4. Export from `index.ts`
5. Register in `@/element/registerComponents.ts`

## Example

```tsx
import { forwardRef } from "react";
import { Streamlit } from "streamlit-component-lib";
import { BaseComponent } from "@/components/ai-elements/base-component";

export interface StMyComponentProps {
    someProp: string;
}

export const StMyComponent = forwardRef<HTMLDivElement, StMyComponentProps>((props, ref) => {
    const handleChange = (value: string) => {
        Streamlit.setComponentValue({ value });
    };

    return (
        <div ref={ref}>
            <BaseComponent {...props} onChange={handleChange} />
        </div>
    );
});

StMyComponent.displayName = "StMyComponent";
```

