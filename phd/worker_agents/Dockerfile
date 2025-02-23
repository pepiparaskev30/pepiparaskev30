# Use the official Python 3.11 slim image as the base
FROM python:3.11-slim

# Install dependencies (including gfortran for SciPy)
RUN apt-get update && apt-get install -y \
    wget curl g++ gfortran \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements.txt
COPY requirements.txt /app/

# Install Python packages **without AVX optimizations**
RUN pip install --no-cache-dir -r requirements.txt \
    --no-binary numpy,scipy,tensorflow,torch  # Force build without AVX

# Copy application code
COPY utilities.py main.py \
    LSTM_attention_model_training.py \
    elasticweightconsolidation.py evaluation_metrics.py /app/

# Set the entry point
CMD ["python", "main.py"]
