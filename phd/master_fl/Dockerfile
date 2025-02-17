# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Install wget and curl in a single RUN command to reduce layers
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create directories for saving files and logs in a single RUN command
RUN mkdir -p /app/master_received_weights_json \
            /app/nodes_notebook \
            /app/federated_send_results \
            /app/aggregated_json_files



# Set the working directory in the container
WORKDIR /app

# Copy the required files into the container
COPY requirements.txt sent_master_FL_weights_api.py utilities.py federated_weight_aggregation.py /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the entry point to the shell script
# Define the command to run your application


CMD ["sh", "-c", "python sent_master_FL_weights_api.py & federated_weight_aggregation.py"]
