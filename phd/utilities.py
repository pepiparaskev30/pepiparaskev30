from kubernetes import client, config
import os
import re
import requests
import json



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



# Function to query Prometheus for CPU and Memory metrics
def get_prometheus_metrics(prometheus_url):
    # Function to query Prometheus for a given metric
    def query_prometheus(query):
        # Prepare the Prometheus query API URL
        url = f"{prometheus_url}/api/v1/query"
        
        # Make the request
        params = {'query': query}
        response = requests.get(url, params=params)
        
        # If the request was successful (HTTP status 200)
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            
            # Check for query results
            if data.get('status') == 'success':
                return data['data']['result']
            else:
                print(f"Error in Prometheus query: {data.get('error')}")
        else:
            print(f"Failed to fetch data from Prometheus. HTTP Status: {response.status_code}")
        
        return []

    # Query for CPU metrics (node_cpu_seconds_total)
    cpu_query = 'rate(node_cpu_seconds_total[1m])'

    # Query for Memory metrics (node_memory_MemAvailable_bytes)
    memory_query = 'node_memory_MemAvailable_bytes'

    # Fetch CPU data
    cpu_data = query_prometheus(cpu_query)

    # Fetch Memory data
    memory_data = query_prometheus(memory_query)

    # Print the results for CPU metrics
    print("CPU Metrics:")
    if cpu_data:
        for cpu in cpu_data:
            for element in cpu:
                if element['mode'] = "iowait":
                    cpu_metric = {"cpu": "iowait", "value":element['value'][1]}
                    print(cpu_metric)
    else:
        print("No CPU data available.")

    # Print the results for Memory metrics
    print("\nMemory Metrics:")
    if memory_data:
        for memory in memory_data:
            memory_metric = {"memory":"node_memory_MemAvailable_bytes", "value": memory["vaue"][1]}
    else:
        print("No memory data available.")


