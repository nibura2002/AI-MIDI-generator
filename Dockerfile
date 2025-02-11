FROM python:3.12-slim

# Install system dependencies required for Poetry and building packages.
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Install Poetry.
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory.
WORKDIR /app

# Copy pyproject.toml and (if available) poetry.lock to leverage Docker cache.
COPY pyproject.toml poetry.lock* /app/

# Install dependencies via Poetry without creating a virtual environment.
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# Copy the rest of the application source code.
COPY . /app

# Expose the port Streamlit will run on.
EXPOSE 8501

# Set environment variables for Streamlit to run in headless mode.
ENV STREAMLIT_SERVER_HEADLESS true
ENV STREAMLIT_SERVER_PORT 8501

# Start the Streamlit app.
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.enableCORS", "false"]