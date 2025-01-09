from datetime import time
from kubernetes import client, config
import os
import time

def get_node_ip(node_name):
    # Load in-cluster configuration (inside the pod)
    config.load_incluster_config()
    
    # Create a Kubernetes API client
    v1 = client.CoreV1Api()
    
    # Get the details of the node by name
    node = v1.read_node(name=node_name)
    
    # Extract the internal IP from the node's addresses
    for address in node.status.addresses:
        if address.type == "InternalIP":
            return address.address

    return None

# Example usage
if __name__ == "__main__":
    while True:
        print("Hello")
        time.sleep(10)
