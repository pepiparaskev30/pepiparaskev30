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
    zlib1g-dev \
    unzip \
    clang \
    && rm -rf /var/lib/apt/lists/*

# Install Bazel manually (Corrected URL)
RUN wget https://github.com/bazelbuild/bazel/releases/download/6.5.0/bazel-6.5.0-linux-x86_64
RUN chmod +x bazel-6.5.0-linux-x86_64
RUN mv bazel-6.5.0-linux-x86_64 /usr/local/bin/bazel

# Verify Bazel installation
RUN bazel --version

# Clone TensorFlow repository
RUN git clone https://github.com/tensorflow/tensorflow.git

# Change into TensorFlow directory
WORKDIR /tensorflow

# Set environment variables to configure TensorFlow build
ENV TF_NEED_CLANG=0
ENV TF_NEED_CUDA=0
ENV TF_NEED_ROCM=0
ENV TF_SET_ANDROID_WORKSPACE=0
ENV TF_DOWNLOAD_CLANG=0
ENV TF_ENABLE_XLA=0
ENV TF_NEED_OPENCL=0
ENV TF_NEED_OPENCL_SYCL=0
ENV TF_NEED_MPI=0
ENV TF_NEED_GCP=0
ENV TF_NEED_HDFS=0
ENV TF_NEED_S3=0
ENV TF_NEED_KAFKA=0
ENV TF_NEED_JEMALLOC=1
ENV TF_NEED_GDR=0
ENV TF_NEED_VERBS=0
ENV TF_NEED_LIBPCI=0
ENV TF_NEED_AWS=0
ENV TF_NEED_NCLI=0
ENV TF_NEED_OPENSSL=1

# Configure TensorFlow build without AVX optimizations
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
