# Use the official Python 3.11 image as the base image
FROM python:3.11-slim

#path to save the models
WORKDIR /app/saved_models 
#path to save the weights
WORKDIR /app/weights_path
#path to save the logs
WORKDIR /app/log_path_file
#path to save the evaluation results
WORKDIR /app/evaluation_results
# path to send the federated weights
WORKDIR /app/federated_send_results



# Set the working directory in the container
WORKDIR /app

# Install the Kubernetes Python client
RUN pip install kubernetes

# Copy the Python script into the container
COPY name_node.py /app/name_node.py

# Command to run the script
CMD ["python", "name_node.py"]