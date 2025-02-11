# Use the official Python 3.11 slim image as the base image
# fdl master weights receive
FROM python:3.11-slim

# Install wget and curl in a single RUN command to reduce layers
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create directories for saving files and logs in a single RUN command
RUN mkdir -p /app/master_received_weights_json \
            /app/node_notebook

# Set the working directory in the container
WORKDIR /app

#copy proper files
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY utilities.py /app

# Set the entry point to the shell script
# Define the command to run your application
CMD ["uvicorn", "fed_master:app", "--host", "0.0.0.0", "--port", "8002"]