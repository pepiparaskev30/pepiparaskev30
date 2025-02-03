# Stage 1: Install dependencies in a separate build stage
FROM python:3.11-slim as build

# Install wget, curl, and other required system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt to install dependencies
COPY requirements.txt /app/
WORKDIR /app

# Install Python dependencies (without cache to keep the image lean)
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image (only includes runtime dependencies)
FROM python:3.11-slim

# Copy the installed dependencies from the build stage
COPY --from=build /usr/local /usr/local

# Install minimal system dependencies (if required by your code)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create directories for saving files and logs
RUN mkdir -p /app/saved_models \
    /app/weights_path \
    /app/log_path_file \
    /app/evaluation_results \
    /app/federated_send_results \
    /app/data_generation_path \
    /app/json_weights \
    /app/federated_received_results \
    /app/federated_send_results 

# Set the working directory in the container
WORKDIR /app

# Create an empty CSV file and add headers
RUN echo "timestamp,cpu,mem,network_receive,network_transmit,load" > /app/data_generation_path/data.csv

# Copy Python scripts and necessary files into the container
COPY . /app/




# Set the entry point to the shell script
CMD ["python", "test.py"]
