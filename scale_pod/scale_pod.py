import os
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kubernetes import client, config

# Load Kubernetes configuration (assuming kubectl config is set)
config.load_kube_config()

# FastAPI app initialization
app = FastAPI()

# Kubernetes API client
v1 = client.AppsV1Api()
v1_core = client.CoreV1Api()

# Define BaseModel to handle the input parameters
class DeploymentRequest(BaseModel):
    prefix: str
    action: str
    replicas: int
    namespace: str = "default"  # Default to "default" if not provided

@app.post("/update_replicas")
async def update_replicas(request: DeploymentRequest):
    """
    Endpoint to update the replica count for a given deployment.
    """
    deployment_name = f"{request.prefix}-deployment"
    namespace = request.namespace

    try:
        # Fetch the current deployment
        deployment = v1.read_namespaced_deployment(deployment_name, namespace)
        
        # Update the replica count in the deployment
        deployment.spec.replicas = request.replicas

        # Apply the patch to update the deployment
        v1.patch_namespaced_deployment(deployment_name, namespace, deployment)

        # Respond with the updated replica count
        return {"message": f"Replica count for {deployment_name} updated to {request.replicas}", "status": "success"}

    except client.exceptions.ApiException as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
