# Stage 1: Build TensorFlow
FROM python:3.11-slim

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    zlib1g-dev \
    unzip \
    clang \
    patch \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Install other dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python scripts and other necessary files into the container
COPY utilities.py main.py \
    LSTM_attention_model_training.py \
    elasticweightconsolidation.py evaluation_metrics.py /app/

# Set the entry point to the shell script
CMD ["python", "main.py"]
