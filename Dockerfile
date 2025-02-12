FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy the entire project files
COPY . .

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false 
RUN poetry install --only main,extras

# Copy application code
COPY api/ .

# Expose the API port
EXPOSE 8765

# Run the API
CMD ["poetry", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8765"]