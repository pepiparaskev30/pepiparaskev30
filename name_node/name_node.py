from kubernetes import client, config
import os, json
import time

SAVED_MODELS = "./saved_models"


def retrieve_information():
    # Load in-cluster configuration
    try:
        config.load_incluster_config()

    except Exception as e:
        print("Could not load in-cluster config, falling back to local kube config.")
        config.load_kube_config()

    # Create an instance of the CoreV1Api to interact with the Kubernetes API
    v1 = client.CoreV1Api()
    # Create an API client instance
    v1_apps = client.AppsV1Api()

    # Get the pod name and namespace from the environment (set by Downward API)
    pod_name = os.getenv('POD_NAME')
    namespace = os.getenv('POD_NAMESPACE')

    if not pod_name or not namespace:
        raise Exception("POD_NAME and POD_NAMESPACE environment variables must be set!")

    # List pods in the namespace and find the current pod's node
    pod_info = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    node_name = pod_info.spec.node_name

    # Print the node name
    node_name_propagation = node_name
    
    # List all deployments across all namespaces
    deployments = v1_apps.list_deployment_for_all_namespaces(watch=False)

    # Filter deployments whose names start with 's'
    filtered_deployments = [
        dep.metadata.name
        for dep in deployments.items
        if dep.metadata.name and dep.metadata.name.startswith("s")
    ]

    # Print the filtered deployments
    if filtered_deployments:
        print("Deployments starting with 's':")
        for deployment in filtered_deployments:
            deployment_file = deployment[0:2]
    else:
        deployment_file = None

    return node_name_propagation, deployment_file

if __name__ == "__main__":
    node_name_propagation, deployment_file = retrieve_information()
    example_dict = {"a":12, "b":13, "Name": "Pepi"}
    # Write the dictionary to the file in JSON format
    with open(SAVED_MODELS+"/"+"data.json", 'w') as json_file:
        json.dump(example_dict, json_file, indent=4)  # `indent=4` formats the JSON nicely
    while True:
        print(f"service name: {deployment_file}")
        print(f"Node name: {node_name_propagation}")
        time.sleep(10)



