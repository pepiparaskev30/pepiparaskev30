# Stage 1: Build TensorFlow
FROM python:3.11-slim AS build-stage

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Bazel manually
RUN wget https://github.com/bazelbuild/bazel/releases/download/6.0.0/bazel_6.0.0-linux-x86_64.deb
RUN dpkg -i bazel_6.0.0-linux-x86_64.deb
RUN rm bazel_6.0.0-linux-x86_64.deb

# Clone TensorFlow repository
RUN git clone https://github.com/tensorflow/tensorflow.git

# Change into TensorFlow directory
WORKDIR /tensorflow

# Configure TensorFlow build without AVX
RUN ./configure

# Build TensorFlow without AVX optimizations
RUN bazel build --config=opt --copt=-mno-avx --copt=-mno-avx2 //tensorflow/tools/pip_package:build_pip_package

# Create a pip package
RUN bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg

# Stage 2: Runtime Environment
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the pre-built TensorFlow package from the build stage
COPY --from=build-stage /tmp/tensorflow_pkg/tensorflow-*.whl /tmp/

# Install TensorFlow from the package
RUN pip install --no-cache-dir /tmp/tensorflow-*.whl

# Install other dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python scripts and other necessary files into the container
COPY utilities.py main.py \
    LSTM_attention_model_training.py \
    elasticweightconsolidation.py evaluation_metrics.py /app/

# Set the entry point to the shell script
CMD ["python", "main.py"]
