from kubernetes import client, config
import threading
from queue import Queue
import os
import urllib.parse
import requests
from datetime import datetime
import time

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")



class Gatherer:
    # Flag to check if the threads are ready to collect information
    ready_flag = True
    # Lists to store the results used by CA, RL and GNN
    prometheus_data_queue = Queue()

    # Amount of time to wait before starting a new thread
    wait_time = int(os.getenv('WAIT_TIME', '55'))

    # Start the threads
    def start_thread():
        # Start a CA thread
        threading.Thread(target=Gatherer.flush_data).start()

    # Start a thread and when it finishes, start another one
    def flush_data():
        start_time = time.time()
        N = Gatherer.prometheus_data_queue.qsize()

        data_list = []
        for i in range(N):
            data_list.append(Gatherer.prometheus_data_queue.get())

        Gatherer.ready_flag = False
        print(data_formulation(data_list), flush=True)
        Gatherer.ready_flag = True

        end_time = time.time()
        sum_time = end_time - start_time

        # If the time is less than the wait time, sleep for the difference
        if sum_time < Gatherer.wait_time:
            time.sleep(Gatherer.wait_time - sum_time)

        # Start a new use_CA thread
        threading.Thread(target=Gatherer.flush_data).start()
        return

# Function to retrieve the internal IP of a node by its name
def get_node_ip_from_name(node_name):
    config.load_incluster_config()  # Load cluster config
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    for address in node.status.addresses:
        if address.type == "InternalIP":
            return address.address
    return None


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
def gather_metrics_for_15_seconds(node_name):
    # Resolve node IP from node name
    node_ip = get_node_ip_from_name(node_name)
    if not node_ip:
        print(f"Could not resolve IP for node: {node_name}")
        return

    #print(f"Monitoring metrics for node {node_name} (IP: {node_ip})")

    # Adjust queries to filter by node's IP
    cpu_query = f'100 * avg(rate(node_cpu_seconds_total{{mode="user",instance="{node_ip}:9100"}}[5m])) by (instance)'
    memory_query = f'100 * (node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}} - node_memory_MemAvailable_bytes{{instance="{node_ip}:9100"}}) / node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}}'

    rows = []


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

    # Transform data into the specified format
    data = {
        "timestamp": [row["timestamp"] for row in rows],
        "cpu": [row["cpu"] for row in rows],
        "mem": [row["mem"] for row in rows]
    }
    return data

def data_formulation(data_flushed:list):
    timestamp_list,cpu_list,mem_list  = [],[],[]
    for resource_dictionary in data_flushed:
        for k, v in resource_dictionary.items():
            if k == "timestamp":
                timestamp_list.append(v[0])
            if k == "cpu":
                cpu_list.append(v[0])
            if k == "mem":
                mem_list.append(v[0])
    data = {"timestamp":timestamp_list, "cpu": cpu_list, "mem": mem_list}

    return data 


