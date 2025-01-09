from kubernetes import client, config

# Function to retrieve the internal IP of a node by its name
def get_node_ip_from_name(node_name):
    config.load_incluster_config()  # Load cluster config
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    for address in node.status.addresses:
        if address.type == "InternalIP":
            return address.address
    return None
