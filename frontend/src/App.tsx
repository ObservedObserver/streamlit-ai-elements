import { useRef, createElement } from 'react';
import { ComponentProps, withStreamlitConnection } from 'streamlit-component-lib';
import { TooltipProvider } from '@/components/ui/tooltip';

import { useAutoHeight } from './hooks/useAutoHeight';
import { ComponentCollection, ComponentName } from './element/registerComponents';

type AppArgs = { 
    component: ComponentName; 
    props?: any; 
    [key: string]: any 
};

const App = withStreamlitConnection(function App(cprops: ComponentProps) {
    const { args } = cprops;
    const { component, props = {} } = args as AppArgs;
    const container = useRef(null);
    const safeHeight = args.safeHeight ?? 10;
    
    if (import.meta.env.DEV) {
        console.log('DEV MODE - Component:', component, 'Props:', props);
    }
    
    // Auto-adjust height based on content
    useAutoHeight(container, safeHeight);
    
    // Get the component from the registry
    const Component = ComponentCollection[component];
    
    if (!Component) {
        return <div ref={container}>
            <p style={{ color: 'red' }}>Component "{component}" not found</p>
        </div>;
    }
    
    return (
        <TooltipProvider>
            <div>
                {createElement(Component, { ...props, ref: container })}
            </div>
        </TooltipProvider>
    );
});

export default App;
