# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Install necessary build dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    python3-dev \
    build-essential \
    cmake \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy requirements file
COPY requirements.txt /app/

# Install necessary Python packages without AVX
RUN pip install --no-cache-dir -r requirements.txt \
    --no-binary numpy,scipy,tensorflow,torch
# Copy application code
COPY utilities.py main.py \
    LSTM_attention_model_training.py \
    elasticweightconsolidation.py evaluation_metrics.py /app/

# Set the entry point
CMD ["python", "main.py"]
