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



# Function to gather metrics for 15 seconds for a specific node
def gather_metrics_for_15_seconds(node_name):
    # Resolve node IP from node name
    node_ip = get_node_ip_from_name(node_name)
    if not node_ip:
        print(f"Could not resolve IP for node: {node_name}")
        return

    print(f"Monitoring metrics for node {node_name} (IP: {node_ip})")

    # Adjust queries to filter by node's IP
    cpu_query = f'100 * avg(rate(node_cpu_seconds_total{{mode="user",instance="{node_ip}:9100"}}[5m])) by (instance)'
    memory_query = f'100 * (node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}} - node_memory_MemAvailable_bytes{{instance="{node_ip}:9100"}}) / node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}}'

    rows = []

    while len(rows) < 10:  # Collect 10 data points
        # Query CPU usage
        cpu_results = query_metric(cpu_query)

        # Query Memory usage
        memory_results = query_metric(memory_query)

        # Collect current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Extract CPU and Memory usage
        for cpu_result in cpu_results:
            instance = cpu_result['metric'].get('instance', 'unknown')
            cpu_value = float(cpu_result['value'][1])  # The value is a [timestamp, value] pair

            memory_value = None
            for mem_result in memory_results:
                if mem_result['metric'].get('instance') == instance:
                    memory_value = float(mem_result['value'][1])
                    break

            rows.append({
                "timestamp": current_time,
                "cpu": cpu_value,
                "mem": memory_value
            })

        time.sleep(15)

    # Transform data into the specified format
    data = {
        "timestamp": [row["timestamp"] for row in rows],
        "cpu": [row["cpu"] for row in rows],
        "mem": [row["mem"] for row in rows]
    }
    return data
