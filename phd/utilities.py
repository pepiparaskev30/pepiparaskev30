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

def get_metrics(url):
    """
    Fetches the raw metrics from the Node Exporter /metrics endpoint.
    
    :param url: The URL of the Node Exporter (e.g., http://localhost:9100/metrics)
    :return: Raw metrics data as a string
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching metrics from {url}: {e}")
        return None

def parse_cpu_metrics(metrics_data):
    """
    Parses CPU-related metrics from the raw metrics data.
    
    :param metrics_data: Raw metrics data (string)
    :return: A dictionary with CPU metrics
    """
    cpu_metrics = {}
    
    # Match 'cpu' related metrics, e.g., `node_cpu_seconds_total{mode="user",cpu="0"} 12.34`
    cpu_pattern = re.compile(r'node_cpu_seconds_total\{mode="(.*?)",cpu="(.*?)"\}\s+([0-9\.]+)')
    
    for match in cpu_pattern.finditer(metrics_data):
        mode = match.group(1)
        cpu = match.group(2)
        value = float(match.group(3))
        
        if cpu not in cpu_metrics:
            cpu_metrics[cpu] = {}
        
        cpu_metrics[cpu][mode] = value
    
    return cpu_metrics

def parse_memory_metrics(metrics_data):
    """
    Parses memory-related metrics from the raw metrics data.
    
    :param metrics_data: Raw metrics data (string)
    :return: A dictionary with memory metrics
    """
    memory_metrics = {}
    
    # Match memory usage, e.g., `node_memory_MemTotal_bytes 8192071680`
    memory_pattern = re.compile(r'node_memory_(.*?bytes)\s+([0-9]+)')
    
    for match in memory_pattern.finditer(metrics_data):
        metric_name = match.group(1)
        value = int(match.group(2))
        memory_metrics[metric_name] = value
    
    return memory_metrics

def display_metrics(cpu_metrics, memory_metrics):
    """
    Display the parsed CPU and Memory metrics in a readable format.
    
    :param cpu_metrics: Dictionary of CPU metrics
    :param memory_metrics: Dictionary of memory metrics
    """
    print("\n--- CPU Metrics ---")
    for cpu, stats in cpu_metrics.items():
        print(f"CPU {cpu}:")
        for mode, value in stats.items():
            print(f"  {mode}: {value:.2f} seconds")
    
    print("\n--- Memory Metrics ---")
    for metric, value in memory_metrics.items():
        print(f"{metric}: {value:,} bytes")





