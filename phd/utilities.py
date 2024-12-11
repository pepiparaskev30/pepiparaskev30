from kubernetes import client, config
import os
import re
import requests



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
            print(filtered_deployments)
            for deployment in filtered_deployments:
                deployment_file = deployment[0:2]
        else:
            deployment_file = None

        
    except Exception as e:
        print("Could not load in-cluster config, Not connectedto K8s")
        node_name_propagation, deployment_file = None, None
    
    return node_name_propagation, deployment_file






def get_node_metrics(NODE_EXPORTER_METRICS_URL):
    # Query the Node Exporter metrics endpoint
    response = requests.get(NODE_EXPORTER_METRICS_URL)
    
    if response.status_code != 200:
        raise Exception(f"Failed to connect to Node Exporter metrics endpoint, status code: {response.status_code}")
    
    # Debugging: Output response text to verify contents
    print("Node Exporter Response:")
    
    # Parse CPU usage from the response using regex
    cpu_usage_match = re.search(r'node_cpu_seconds_total\{mode="user"\} (\d+\.\d+)', response.text)
    if not cpu_usage_match:
        raise Exception("Could not find expected CPU metrics in Node Exporter response")
    
    cpu_usage = float(cpu_usage_match.group(1))

    # Parse memory active bytes from the response using regex
    memory_available_match = re.search(r'node_memory_Active_bytes (\d+)', response.text)
    if not memory_available_match:
        raise Exception("Could not find expected memory metrics in Node Exporter response")
    
    memory_available = float(memory_available_match.group(1))

    return {
        "cpu_usage_seconds_user": cpu_usage,
        "memory_active_bytes": memory_available
    }
