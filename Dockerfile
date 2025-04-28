# Use official lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir fastapi uvicorn gunicorn

# Expose a default port (optional, mostly for local Docker use)
EXPOSE 8888

# Use environment variable PORT, default to 8000 if not set
ENV PORT=8888
ENV WORKERS=2

# Start Gunicorn with Uvicorn workers
CMD ["sh", "-c", "gunicorn main:app --workers $WORKERS --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT"]
