from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import re



import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Retrieve the Kubernetes environment variables
kubernetes_host = os.getenv("KUBERNETES_SERVICE_HOST")
kubernetes_port = os.getenv("KUBERNETES_SERVICE_PORT")

# Log the environment variables
logging.debug(f"Kubernetes API Server Host: {kubernetes_host}")
logging.debug(f"Kubernetes API Server Port: {kubernetes_port}")

# Optionally, you can also check the full set of environment variables to ensure the pod is correctly configured
all_env_vars = os.environ
logging.debug(f"All Environment Variables: {all_env_vars}")

# Initialize FastAPI app
app = FastAPI()

# Define the request body using Pydantic
class ScaleRequest(BaseModel):
    action: str
    prefix: str
    namespace: str = "default"
    replicas: int = 3



# Kubernetes API client setup
def scale_deployment(namespace: str, deployment_name: str, replicas: int):
    try:
        # Load kube config from within the pod
        config.load_incluster_config()

        # Create an instance of the AppsV1Api
        apps_v1 = client.AppsV1Api()

        # Get the current deployment
        deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)

        # Update the replica count
        deployment.spec.replicas = replicas

        # Apply the updated deployment
        apps_v1.replace_namespaced_deployment(deployment_name, namespace, deployment)

        print(f"Deployment {deployment_name} scaled to {replicas} replicas.")
        return f"Deployment {deployment_name} scaled to {replicas} replicas."

    except ApiException as e:
        print(f"Error scaling deployment: {e}")
        raise HTTPException(status_code=400, detail="Error scaling deployment")

# FastAPI route to handle scaling requests
@app.post("/scale")
async def scale_replicas(request: ScaleRequest):
    # Validate that action is "scale"
    if request.action != "scale":
        raise HTTPException(status_code=400, detail="Invalid action. Use 'scale' to scale the deployment.")
    
    # Validate that the prefix is in the expected format (s1, s2, s3, etc.)
    valid_prefixes = ["s1", "s2", "s3"]  # List all valid prefixes
    if request.prefix not in valid_prefixes:
        raise HTTPException(status_code=400, detail=f"Invalid prefix. Allowed values are: {', '.join(valid_prefixes)}.")

    # Ensure the deployment name follows the format
    deployment_name = f"{request.prefix}-deployment"
    print(f"Scaling deployment: {deployment_name} in namespace {request.namespace} to {request.replicas} replicas.")

    # Call the function to scale the deployment
    result = scale_deployment(request.namespace, deployment_name, request.replicas)

    return {"message": result}

