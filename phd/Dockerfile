# Stage 1: Build stage
FROM python:3.11-alpine as builder

# Install essential system packages
RUN apk add --no-cache \
    wget \
    curl

# Set the working directory
WORKDIR /app

# Copy requirements.txt into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python scripts into the container
COPY main.py data_generation.py utilities.py test.py LSTM_attention_model_training.py /app/

# Stage 2: Final stage
FROM python:3.11-alpine

# Create directories for saving files and logs
RUN mkdir -p /app/saved_models \
    /app/weights_path \
    /app/log_path_file \
    /app/evaluation_results \
    /app/federated_send_results \
    /app/data_generation_path

# Set the working directory
WORKDIR /app

# Copy only the necessary files from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

# Create an empty CSV file and add headers
RUN echo "timestamp,cpu,mem,network_receive,network_transmit,load" > /app/data_generation_path/data.csv

# Set the entry point to the shell script
CMD ["python", "test.py"]