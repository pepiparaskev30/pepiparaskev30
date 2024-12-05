from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
# Initialize FastAPI
app = FastAPI()

# Define the request payload schema using Pydantic
class ScaleRequest(BaseModel):
    action: str
    prefix: str
    namespace: str
    replicas: int

def load_k8s_config():
    try:
        # Try to load in-cluster config
        config.load_incluster_config()
        logging.info("Successfully loaded in-cluster Kubernetes config.")
    except Exception as e:
        logging.warning(f"In-cluster config failed: {str(e)}")


# Create the scale deployment function
def scale_deployment(prefix: str, namespace: str, replicas: int):
    load_k8s_config()
    apps_v1 = client.AppsV1Api()
    
    # Specify the deployment name (using prefix)
    deployment_name = f"{prefix}-deployment"
    try:
            # Make the API call to update the deployment replicas
            api_response = apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name, 
                namespace=ScaleRequest.namespace, 
                body={'spec': {'replicas': ScaleRequest.replicas}}
    )
            return {"message": f"Scaled {deployment_name} to {replicas} replicas"}
    except ApiException as e:
        raise HTTPException(status_code=400, detail=f"Error scaling deployment: {str(e)}")
    '''
    return deployment_name, namespace, replicas

    
    '''
# Define the POST endpoint to scale deployments
    return deployment_name
@app.post("/scale-deployment")

async def scale_deployment_api(payload: ScaleRequest):
    if payload.action != "scale":
        raise HTTPException(status_code=400, detail="Action must be 'scale'")

    # Scale the deployment
    response = scale_deployment(payload.prefix, payload.namespace, payload.replicas)
    return response
