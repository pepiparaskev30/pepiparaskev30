# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ../cpu_task_api.py .

# Expose port
EXPOSE 8003

# Run command when container starts
CMD ["python", "cpu-app-deployment.py"]
