# Use the official Python 3.11 image as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install the Kubernetes Python client
RUN pip install kubernetes

# Copy the Python script into the container
COPY name_node.py /app/name_node.py

# Command to run the script
CMD ["python", "name_node.py"]