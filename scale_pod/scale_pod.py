from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Initialize FastAPI
app = FastAPI()

# Define the request payload schema using Pydantic
class ScaleRequest(BaseModel):
    action: str
    prefix: str
    namespace: str
    replicas: int

# Load the Kubernetes configuration from the local machine (minikube context)
def load_k8s_config():
    try:
        # This will try to load the Kubernetes config from the default location
        config.load_kube_config()  # for local development (like minikube)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading Kubernetes config")

# Create the scale deployment function
def scale_deployment(prefix: str, namespace: str, replicas: int):
    # Load K8s config
    load_k8s_config()
    
    # Create an API client for the AppsV1 API
    api = client.AppsV1Api()
    
    # Specify the deployment name (using prefix)
    deployment_name = f"{prefix}-deployment"
    
    # Define the body of the scale request
    body = {
        "spec": {
            "replicas": replicas
        }
    }

    try:
        # Make the API call to update the deployment replicas
        api.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=body)
        return {"message": f"Scaled {deployment_name} to {replicas} replicas"}
    except ApiException as e:
        raise HTTPException(status_code=400, detail=f"Error scaling deployment: {str(e)}")

# Define the POST endpoint to scale deployments
@app.post("/scale-deployment")
async def scale_deployment_api(payload: ScaleRequest):
    if payload.action != "scale":
        raise HTTPException(status_code=400, detail="Action must be 'scale'")

    # Scale the deployment
    response = scale_deployment(payload.prefix, payload.namespace, payload.replicas)
    return response
