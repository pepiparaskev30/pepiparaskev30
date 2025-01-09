import os
import time
import urllib.parse
import requests
from kubernetes import client, config
from datetime import datetime
from utilities import get_node_ip_from_name
from multiprocessing import Queue

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
NODE_NAME = os.getenv("NODE_NAME")


# Function to query Prometheus metrics
def query_metric(promql_query):
    encoded_query = urllib.parse.quote(promql_query)
    url = f"{PROMETHEUS_URL}/api/v1/query?query={encoded_query}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return data.get('data', {}).get('result', [])
            else:
                print(f"Query failed: {data.get('error')}")
        else:
            print(f"Error: HTTP {response.status_code}, {response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    return []


# Function to gather metrics for 15 seconds for a specific node
def gather_metrics_for_15_seconds(node_name, queue):
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

    # Push data to the queue
    queue.put(data)
    print("Data batch sent to the processor.")

    return data


# Example usage
if __name__ == "__main__":
    data_queue = Queue()  # Shared queue for inter-process communication
    node_name = NODE_NAME

    while True:
        gather_metrics_for_15_seconds(node_name, data_queue)
        time.sleep(3)
