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
            for deployment in filtered_deployments:
                deployment_file = deployment[0:2]
        else:
            deployment_file = None

        
    except Exception as e:
        print("Could not load in-cluster config, Not connectedto K8s")
        node_name_propagation, deployment_file = None, None
    
    return node_name_propagation, deployment_file



def get_node_metrics(PROMETHEUS_URL):
    # Query Prometheus for CPU usage and memory usage using PromQL
    response = requests.get(PROMETHEUS_URL, params={"query": 'node_cpu_seconds_total{mode="user"}'})
    if response.status_code != 200:
        raise Exception("Failed to connect to Prometheus API")

    # Parse the CPU usage data from the response
    cpu_usage_data = response.json()
    if not cpu_usage_data.get("data") or not cpu_usage_data["data"].get("result"):
        raise Exception("Could not find expected metrics in Prometheus response")

    cpu_usage = float(cpu_usage_data["data"]["result"][0]["value"][1])  # Parse the value field

    # Query Prometheus for memory usage data
    response = requests.get(PROMETHEUS_URL, params={"query": 'node_memory_Active_bytes'})
    if response.status_code != 200:
        raise Exception("Failed to connect to Prometheus API for memory metrics")

    memory_data = response.json()
    if not memory_data.get("data") or not memory_data["data"].get("result"):
        raise Exception("Could not find expected memory metrics in Prometheus response")

    memory_available = float(memory_data["data"]["result"][0]["value"][1])  # Parse the value field

    return {
        "cpu_usage_seconds_user": cpu_usage,
        "memory_active_bytes": memory_available
    }
