# Use the official Python 3.11 image as the base image
FROM python:3.11-slim

# Install wget and curl
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create directories for saving files and logs
RUN mkdir -p /app/saved_models \
    /app/weights_path \
    /app/log_path_file \
    /app/evaluation_results \
    /app/federated_send_results \
    /app/data_generation_path

# Set the working directory in the container
WORKDIR /app
# Create an empty CSV file and add headers
RUN echo "timestamp,cpu,mem,network_receive,network_transmit,network_receive_packets,network_transmit_packets,network_receive_drops,network_transmit_drops,network_receive_errors,network_transmit_errors,disk_read,disk_write,disk_usage,load,uptime" > /app/data_generation_path/data.csv

# Copy requirements.txt into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python scripts and other necessary files into the container
COPY main.py /app/
COPY data_generation.py /app/
COPY utilities.py /app/
COPY test.py /app/

WORKDIR /app
# Set the entry point to the shell script
CMD ["python", "test.py"]
