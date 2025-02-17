# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Install required system packages
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/master_received_weights_json \
            /app/federated_send_results \
            /app/aggregated_json_files

# Set the working directory
WORKDIR /app

# Copy application files
COPY requirements.txt sent_master_FL_weights_api.py utilities.py federated_weight_aggregration.py start.sh /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the script is executable
RUN chmod +x /app/start.sh

# Run the startup script
CMD ["/bin/sh", "/app/start.sh"]
