import os
from dotenv import load_dotenv
import streamlit.components.v1 as components

# Load environment variables from .env file
load_dotenv()

# Set to False during development (requires dev server running), True for release
# Load from .env file, default to True if not found
__RELEASE = os.getenv('RELEASE', 'true').lower() in ('true', '1', 'yes')

def declare_component(component_name: str, url="http://localhost:5173", release=__RELEASE):
    """Declare a Streamlit component
    
    Args:
        component_name: Name of the component
        url: Development server URL (used when release=False)
        release: If True, use built files from frontend/dist
    
    Returns:
        Component function
    """
    if not release:
        _component_func = components.declare_component(
            component_name,
            url=url,
        )
    else:
        # When distributing a production version, use the built files
        parent_dir = os.path.dirname(os.path.abspath(__file__))
        build_dir = os.path.join(parent_dir, "../../frontend/dist")
        print(f"build_dir: {build_dir}")
        _component_func = components.declare_component(component_name, path=build_dir)

    return _component_func
