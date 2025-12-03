# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Install wget and curl in a single RUN command to reduce layers
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create directories for saving files and logs in a single RUN command
RUN mkdir -p /app/saved_models \
    /app/weights_path \
    /app/log_path_file \
    /app/evaluation_results \
    /app/federated_send_results \
    /app/data_generation_path \
    /app/json_weights \
    /app/federated_received_results

# Set the working directory in the container
WORKDIR /app

# Create an empty CSV file and add headers in a single RUN command
RUN echo "timestamp,cpu,mem,network_receive,network_transmit,load" > /app/data_generation_path/data.csv

# Copy requirements.txt into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python scripts and other necessary files into the container in a single COPY command
COPY utilities.py main.py \
    LSTM_attention_model_training.py \
    GRU_Controller_training.py \
    elasticweightconsolidation.py evaluation_metrics.py /app/


# Set the entry point to the shell script
CMD ["python", "main.py"]
