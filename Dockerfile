# Use official lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files (Coolify already cloned them into build context)
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir fastapi uvicorn

# Expose port for Uvicorn
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
