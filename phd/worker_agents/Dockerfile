# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Install necessary dependencies and create required directories in a single RUN command
RUN apt-get update && apt-get install -y wget curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/{saved_models,weights_path,log_path_file,evaluation_results,federated_send_results,data_generation_path,json_weights,federated_received_results} \
    && echo "timestamp,cpu,mem,network_receive,network_transmit,load" > /app/data_generation_path/data.csv

# Set the working directory in the container
WORKDIR /app

# Copy and install Python dependencies efficiently
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python scripts and other necessary files into the container in a single COPY command
COPY utilities.py main.py \
    LSTM_attention_model_training.py \
    elasticweightconsolidation.py evaluation_metrics.py /app/


# Set the entry point to the shell script
CMD ["python", "main.py"]
