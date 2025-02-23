# Use a slim Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for building SciPy, NumPy, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install necessary Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Ensure the correct version of gast is installed
RUN pip install --no-cache-dir "gast>=0.5.4"

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt /app/

# Install Python packages WITHOUT AVX optimizations
RUN pip install --no-cache-dir -r requirements.txt \
    --no-binary numpy,scipy,tensorflow,torch  # Force build without AVX

# Copy application code
COPY utilities.py main.py \
    LSTM_attention_model_training.py \
    elasticweightconsolidation.py evaluation_metrics.py /app/

# Set the entry point
CMD ["python", "main.py"]
