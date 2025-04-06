FROM python:3.10-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Configure Poetry to create virtual environments inside the project
RUN poetry config virtualenvs.in-project true

# Set up working directory
WORKDIR /workspace

# Install development tools
RUN pip install black flake8

# Set Python path
ENV PYTHONPATH=/workspace 