import { useEffect } from 'react';
import { Streamlit } from 'streamlit-component-lib';

export function useAutoHeight(
    container: React.RefObject<HTMLElement>,
    safeHeight: number = 10
) {
    useEffect(() => {
        const observer = new ResizeObserver(() => {
            if (container.current) {
                const height = container.current.scrollHeight + safeHeight;
                Streamlit.setFrameHeight(height);
            }
        });

        if (container.current) {
            observer.observe(container.current);
        }

        return () => {
            observer.disconnect();
        };
    }, [container, safeHeight]);
}
