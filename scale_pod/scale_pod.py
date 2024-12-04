from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Manually set the Minikube API server IP and port
# (These values can be obtained from minikube ip and kubectl cluster-info)
os.environ["KUBERNETES_SERVICE_HOST"] = "192.168.49.2"  # Replace with your Minikube IP
os.environ["KUBERNETES_SERVICE_PORT"] = "8443"           # Default port for Kubernetes API

# Retrieve the Kubernetes environment variables
kubernetes_host = os.getenv("KUBERNETES_SERVICE_HOST")
kubernetes_port = os.getenv("KUBERNETES_SERVICE_PORT")

# Initialize FastAPI app
app = FastAPI()

# Define the request body using Pydantic
class ScaleRequest(BaseModel):
    action: str
    prefix: str
    namespace: str
    replicas: int

# Kubernetes API client setup
def scale_deployment(namespace: str, deployment_name: str, replicas: int):
    try:
        # Load kube config from within the pod
        config.load_incluster_config()

        # Create an instance of the AppsV1Api
        apps_v1 = client.AppsV1Api()

        
        print("before error!")
        # Print the deployment name and namespace for debugging
        print(f"Scaling deployment: {deployment_name} in namespace {namespace} to {replicas} replicas.")
        print("error!!!!")
        # Use patch_namespaced_deployment_scale to scale the deployment
        scale_body = {
            'spec': {
                'replicas': replicas
            }
        }
        
        # Call the API to patch the deployment scale
        api_response = apps_v1.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=namespace,
            body=scale_body
        )
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
    valid_prefixes = [request.prefix]  # List all valid prefixes
    if request.prefix not in valid_prefixes:
        raise HTTPException(status_code=400, detail=f"Invalid prefix. Allowed values are: {', '.join(valid_prefixes)}.")

    # Ensure the deployment name follows the format
    deployment_name = f"{request.prefix}-deployment"
    print(f"Scaling deployment: {deployment_name} in namespace {request.namespace} to {request.replicas} replicas.")

    # Call the function to scale the deployment
    result = scale_deployment(request.namespace, deployment_name, request.replicas)

    return {"message": result}
