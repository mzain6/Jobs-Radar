FROM python:3.11-slim

# Install basic tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy dependencies first to leverage caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and all Chromium dependencies automatically
RUN python -m playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Expose port (Render uses dynamic $PORT, but we expose 8000 for local testing)
EXPOSE 8000

# Start uvicorn server, binding to the port provided by Render
CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
