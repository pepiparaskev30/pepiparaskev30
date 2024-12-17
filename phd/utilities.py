from kubernetes import client, config
import os
import re
import requests
import json
import time



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



# Define the Prometheus query with 20-second interval


# Function to query Prometheus and get results
def query_prometheus(prometheus_url):
    query = '100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[20s])) by (instance))'
    # Build the URL for the Prometheus API query endpoint
    url = f"{prometheus_url}/api/v1/query"
    
    # Send the query
    response = requests.get(url, params={'query': query})
    
    # Check if the request was successful
    if response.status_code == 200:
        result = response.json()  # Parse JSON response
        return result
    else:
        print(f"Error querying Prometheus: {response.status_code}")
        return None

# Function to extract CPU utilization from Prometheus query result
def extract_cpu_utilization(query_result):
    if query_result and query_result['status'] == 'success':
        data = query_result['data']['result']
        
        # Loop through the results and print each instance's CPU utilization
        for item in data:
            instance = item['metric']['instance']
            value = item['value'][1]  # The value is the second element in the list
            print(f"Instance: {instance}, CPU Utilization: {value}%")
    else:
        print("No data or query failed.")

# Function to run the query at regular intervals (e.g., every 20 seconds)
def run_query_every_20_seconds(prometheus_url):
    while True:
        result = query_prometheus(prometheus_url)
        extract_cpu_utilization(result)
        
        # Wait for 20 seconds before running the query again
        time.sleep(20)



