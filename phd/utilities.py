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



def get_cpu_usage(url):
    prometheus_url = f'http://{url}/api/v1/query'
    # Define the query inside the function
    query = '100 * avg(1 - rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)'
    
    # Send the HTTP request to Prometheus with the query
    response = requests.get(prometheus_url, params={'query': query})
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response and extract CPU usage data
        data = response.json()['data']['result']
        
        # Prepare list to store CPU usage percentage values
        cpu_usage_percentages = []
        
        # Iterate over the result data and extract the CPU usage value for each instance
        for result in data:
            cpu_usage = result['value'][1]  # CPU usage percentage value
            cpu_usage_percentages.append(float(cpu_usage))  # Convert to float for calculations
        
        # Return the result in the desired format: {'cpu': [value1, value2, ...]}
        return {'cpu': cpu_usage_percentages}
    else:
        print(f"Error querying Prometheus: {response.status_code}")
        return None





