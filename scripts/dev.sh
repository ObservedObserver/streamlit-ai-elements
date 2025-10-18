#!/bin/bash
# Development script for Streamlit AI Elements

# Change to project root
cd "$(dirname "$0")/.."

# Build frontend
echo "Building frontend..."
cd frontend
yarn build
cd ..

# Run streamlit
echo "Starting Streamlit..."
streamlit run demo.py
