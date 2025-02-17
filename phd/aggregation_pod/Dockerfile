# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Install wget and curl in a single RUN command to reduce layers
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the required files into the container
COPY requirements.txt federated_weight_aggregration.py utilities.py /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the entry point to the shell script
# Define the command to run your application


CMD ["python", "federated_weight_aggregration.py"]
