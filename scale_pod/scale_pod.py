
'''
Script that scales within an API the number of replicas
'''
from fastapi import FastAPI, HTTPException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os

# Initialize FastAPI app
app = FastAPI()

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

@app.post("/scale")
async def scale_replicas(action: str, prefix: str, namespace: str = "default", replicas: int = 3):
    if action != "scale":
        raise HTTPException(status_code=400, detail="Invalid action. Use 'scale' to scale the deployment.")
    
    # Validate that prefix is one of the valid options (e.g., s1, s2, s3, ...)
    valid_prefixes = [prefix]
    if prefix not in valid_prefixes:
        raise HTTPException(status_code=400, detail="Invalid prefix. Allowed values are: s1, s2, s3.")
    
    # Construct the deployment name
    deployment_name = f"{prefix}-deployment"
    
    # Call function to scale the deployment
    result = scale_deployment(namespace, deployment_name, replicas)
    return {"message": result}
