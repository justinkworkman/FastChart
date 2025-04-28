# Use official lightweight Python image
FROM python:3.12-slim

# Install git to clone repo
RUN apt-get update && apt-get install -y git

# Set working directory
WORKDIR /app

# Clone your GitHub repository
# (replace the URL below with your actual repo)
RUN git clone https://github.com/justinkworkman/FastChart.git .

# Install required Python packages
RUN pip install --no-cache-dir fastapi uvicorn

# Expose port that Uvicorn will run on
EXPOSE 8000

# Start Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
