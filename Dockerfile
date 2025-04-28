# Use official lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir fastapi uvicorn

# Expose a default port (optional, for local use)
EXPOSE 8888

# Use environment variable PORT, default to 8888 if not set
ENV PORT=8888

# Start Uvicorn and bind to PORT dynamically
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
