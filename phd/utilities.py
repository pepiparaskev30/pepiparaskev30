from kubernetes import client, config
import os



def retrieve_k8s_information():
    # Load in-cluster configuration
    try:
        config.load_incluster_config()
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

        
    except Exception as e:
        print("Could not load in-cluster config, Not connectedto K8s")
        node_name_propagation, deployment_file = None, None
    
    return node_name_propagation, deployment_file

import requests
import re





def get_node_metrics(NODE_EXPORTER_METRICS_URL):
    # Query the node-exporter metrics endpoint
    response = requests.get(NODE_EXPORTER_METRICS_URL)
    if response.status_code != 200:
        raise Exception("Failed to connect to node-exporter metrics endpoint")
    
    # Parse CPU usage from the response
    cpu_usage_match = re.search(r'node_cpu_seconds_total\{mode="user"\} (\d+\.\d+)', response.text)
    memory_available_match = re.search(r'node_memory_Active_bytes (\d+)', response.text)

    if not cpu_usage_match or not memory_available_match:
        raise Exception("Could not find expected metrics in node-exporter response")

    cpu_usage = float(cpu_usage_match.group(1))
    memory_available = float(memory_available_match.group(1))

    return {
        "cpu_usage_seconds_user": cpu_usage,
        "memory_active_bytes": memory_available
    }


    
