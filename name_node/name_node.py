from kubernetes import client, config
import os


def main():
    # Load in-cluster configuration
    try:
        config.load_incluster_config()
    except Exception as e:
        print("Could not load in-cluster config, falling back to local kube config.")
        config.load_kube_config()

    # Create an instance of the CoreV1Api to interact with the Kubernetes API
    v1 = client.CoreV1Api()

    # Get the pod name and namespace from the environment (set by Downward API)
    pod_name = os.getenv('POD_NAME')
    namespace = os.getenv('POD_NAMESPACE')

    if not pod_name or not namespace:
        raise Exception("POD_NAME and POD_NAMESPACE environment variables must be set!")

    # List pods in the namespace and find the current pod's node
    pod_info = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    node_name = pod_info.spec.node_name
    
    # Print the node name
    print(f"Running on node: {node_name}")


if __name__ == "__main__":
    main()


