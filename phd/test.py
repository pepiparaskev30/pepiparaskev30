from kubernetes import client, config

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
    # Replace with the actual node name
    node_name = "minikube"
    internal_ip = get_node_ip(node_name)
    if internal_ip:
        print(f"Internal IP for node {node_name}: {internal_ip}")
    else:
        print(f"Could not find an internal IP for node {node_name}")
