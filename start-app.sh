#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating .env file..."
    
    # If OPENAI_API_KEY environment variable is set, use it
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "Using OpenAI API key from environment variable."
        echo "OPENAI_API_KEY=$OPENAI_API_KEY" > .env
    else
        # Prompt for API key
        echo -n "Enter your OpenAI API key (or set OPENAI_API_KEY in the environment): "
        read api_key
        
        if [ -n "$api_key" ]; then
            echo "OPENAI_API_KEY=$api_key" > .env
        else
            echo "No API key provided. The app may not function correctly."
            echo "OPENAI_API_KEY=your-api-key-here" > .env
        fi
    fi
    
    # Add default model
    echo "OPENAI_MODEL=gpt-4o-mini" >> .env
    echo ".env file created with API configuration."
fi

# Check how we're running the app
if [ -f "/.dockerenv" ] || [ -n "$DOCKER_CONTAINER" ]; then
    # We're in Docker
    echo "Running in Docker environment..."
    streamlit run app.py
else
    # Check if Poetry is installed
    if command -v poetry &> /dev/null; then
        echo "Using Poetry to run the app..."
        # Check if we're in the poetry environment already
        if [ -n "$POETRY_ACTIVE" ]; then
            echo "Poetry environment is active, starting Streamlit..."
            streamlit run app.py
        else
            echo "Activating Poetry environment and starting Streamlit..."
            poetry run streamlit run app.py
        fi
    else
        # Check if we can use Docker Compose
        if command -v docker-compose &> /dev/null; then
            echo "Starting AI Assistant with Docker Compose..."
            docker-compose up
        else
            echo "Neither Poetry nor Docker Compose found. Attempting to run with Python directly..."
            # Try to run with Python directly if all else fails
            pip install -r requirements.txt 2>/dev/null || pip install streamlit openai python-dotenv
            python -m streamlit run app.py
        fi
    fi
fi 