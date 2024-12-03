# Use a base Python image
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Copy the application files into the container
COPY scale_pod.py /app/

# Install the required dependencies (FastAPI, Uvicorn, and Kubernetes client)
RUN pip install --no-cache-dir fastapi uvicorn kubernetes

# Expose port 8000 to access the FastAPI app
EXPOSE 8001

# Command to run the application
CMD ["uvicorn", "scale_pod:app", "--host", "0.0.0.0", "--port", "8001"]
