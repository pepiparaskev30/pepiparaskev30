from kubernetes import client, config
import os
import re
import requests
import json
import pandas



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
    # Query Prometheus for the CPU time series
    query = 'rate(node_cpu_seconds_total{mode!="idle"}[1m])'
    url = f"{prometheus_url}/api/v1/query"
    params = {'query': query}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'success':
            print("Error: Prometheus query failed")
            return None
        
        # Extract the relevant time series data
        result = data['data']['result']
        
        if not result:
            print("Error: No data returned from Prometheus")
            return None
        
        # Normalize the CPU usage (sum the rates of all CPU cores)
        total_cpu_usage = 0
        for series in result:
            values = series['values']
            for timestamp, value in values:
                total_cpu_usage += float(value)
        
        # Return the normalized CPU usage as a percentage
        return total_cpu_usage * 100

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Prometheus: {e}")
        return None


