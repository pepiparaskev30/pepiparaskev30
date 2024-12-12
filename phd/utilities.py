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


def get_node_metrics(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch metrics, status code {response.status_code}")
    
    # Extract CPU metrics
    cpu_metrics = extract_cpu_metrics(response.text)
    
    # Extract memory metrics
    memory_metrics = extract_memory_metrics(response.text)
    
    # Combine both sets of data into one dictionary
    node_metrics = {**cpu_metrics, **memory_metrics}
    
    return node_metrics

    
def extract_cpu_metrics(metrics_data):
    cpu_metrics = {}
    
    # Extract total CPU usage time for each mode (user, system, idle, etc.)
    cpu_usage_pattern = re.compile(r'node_cpu_seconds_total\{cpu="(\d+)",mode="(\w+)"\}\s+(\d+\.\d+)')
    cpu_usage = {}
    for match in cpu_usage_pattern.finditer(metrics_data):
        cpu, mode, value = match.groups()
        value = float(value)
        if cpu not in cpu_usage:
            cpu_usage[cpu] = {}
        cpu_usage[cpu][mode] = value
    
    # Extract CPU idle time for each CPU core
    cpu_metrics["cpu_usage"] = cpu_usage
    
    # Return extracted CPU data
    return cpu_metrics

def extract_memory_metrics(metrics_data):
    memory_metrics = {}
    
    # Extract total memory available, used, and free from the system
    mem_pattern = re.compile(r'go_memstats_(alloc|heap)_bytes\s+(\d+\.\d+)')
    memory_usage = {}
    
    # Memory stats that we will extract
    for match in mem_pattern.finditer(metrics_data):
        metric, value = match.groups()
        value = float(value)
        
        # Categorize the metrics
        if metric == "alloc":
            memory_usage["memory_allocated"] = value
        elif metric == "heap":
            memory_usage["heap_usage"] = value

    # Total system memory from `go_memstats_sys_bytes`
    total_memory_pattern = re.compile(r'go_memstats_sys_bytes\s+(\d+\.\d+)')
    match = total_memory_pattern.search(metrics_data)
    if match:
        memory_usage["total_memory"] = float(match.group(1))

    # Calculate memory used and free (can be estimated from total and heap/allocated memory)
    memory_usage["memory_used"] = memory_usage["total_memory"] - memory_usage.get("heap_usage", 0)
    memory_usage["memory_free"] = memory_usage["total_memory"] - memory_usage["memory_used"]
    
    # Return extracted memory data
    memory_metrics["memory_usage"] = memory_usage
    
    return memory_metrics