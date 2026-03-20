FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create required directories
RUN mkdir -p generated_report logs memory_store prompts

# Expose both backend and frontend ports
EXPOSE 8000

# Health check for the API
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Start the FastAPI server (Render injects $PORT)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
