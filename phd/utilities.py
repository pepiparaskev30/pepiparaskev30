from kubernetes import client, config
import threading
from queue import Queue
import os
import urllib.parse
import requests
from datetime import datetime
import time
import pandas as pd
import csv
from sklearn.impute import SimpleImputer

global header
header = ["timestamp", "cpu", "mem", "network_receive", "network_transmit", "disk_read", "disk_write", "disk_usage", "load", "uptime"]

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
DATA_GENERATION_PATH = "./data_generation_path/data.csv"



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
        print(data_list, flush=True)
        #preprocessing(data_list, DATA_GENERATION_PATH)
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

def gather_metrics_for_15_seconds(node_name):
    # Resolve node IP from node name
    node_ip = get_node_ip_from_name(node_name)
    if not node_ip:
        print(f"Could not resolve IP for node: {node_name}")
        return

    # Adjust queries to filter by node's IP
    cpu_query = f'100 * avg(rate(node_cpu_seconds_total{{mode="user",instance="{node_ip}:9100"}}[5m])) by (instance)'
    memory_query = f'100 * (node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}} - node_memory_MemAvailable_bytes{{instance="{node_ip}:9100"}}) / node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}}'
    
    # Network bandwidth queries
    network_receive_query = f'rate(node_network_receive_bytes_total{{instance="{node_ip}:9100", device!="lo"}}[5m])'
    network_transmit_query = f'rate(node_network_transmit_bytes_total{{instance="{node_ip}:9100", device!="lo"}}[5m])'
    
    # Disk I/O queries
    disk_read_query = f'rate(node_disk_read_bytes_total{{instance="{node_ip}:9100"}}[5m])'
    disk_write_query = f'rate(node_disk_write_bytes_total{{instance="{node_ip}:9100"}}[5m])'
    
    # Disk usage query (for ext4 file systems)
    disk_usage_query = f'100 * (node_filesystem_size_bytes{{instance="{node_ip}:9100",fstype="ext4"}} - node_filesystem_free_bytes{{instance="{node_ip}:9100",fstype="ext4"}}) / node_filesystem_size_bytes{{instance="{node_ip}:9100",fstype="ext4"}}'
    
    # Load average query
    load_query = f'node_load1{{instance="{node_ip}:9100"}}'
    
    # Uptime query
    uptime_query = f'node_time_seconds{{instance="{node_ip}:9100"}}'

    rows = []

    # Querying all metrics
    cpu_results = query_metric(cpu_query)
    memory_results = query_metric(memory_query)
    network_receive_results = query_metric(network_receive_query)
    network_transmit_results = query_metric(network_transmit_query)
    disk_read_results = query_metric(disk_read_query)
    disk_write_results = query_metric(disk_write_query)
    disk_usage_results = query_metric(disk_usage_query)
    load_results = query_metric(load_query)
    uptime_results = query_metric(uptime_query)

    # Collect current timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Extract CPU, Memory, Network, Disk, Load, and Uptime data
    for cpu_result in cpu_results:
        instance = cpu_result['metric'].get('instance', 'unknown')
        cpu_value = float(cpu_result['value'][1])  # The value is a [timestamp, value] pair

        memory_value = None
        for mem_result in memory_results:
            if mem_result['metric'].get('instance') == instance:
                memory_value = float(mem_result['value'][1])
                break

        network_receive_value = None
        for net_recv_result in network_receive_results:
            if net_recv_result['metric'].get('instance') == instance:
                network_receive_value = float(net_recv_result['value'][1])
                break

        network_transmit_value = None
        for net_transmit_result in network_transmit_results:
            if net_transmit_result['metric'].get('instance') == instance:
                network_transmit_value = float(net_transmit_result['value'][1])
                break

        disk_read_value = None
        for disk_read_result in disk_read_results:
            if disk_read_result['metric'].get('instance') == instance:
                disk_read_value = float(disk_read_result['value'][1])
                break

        disk_write_value = None
        for disk_write_result in disk_write_results:
            if disk_write_result['metric'].get('instance') == instance:
                disk_write_value = float(disk_write_result['value'][1])
                break

        disk_usage_value = None
        for disk_usage_result in disk_usage_results:
            if disk_usage_result['metric'].get('instance') == instance:
                disk_usage_value = float(disk_usage_result['value'][1])
                break

        load_value = None
        for load_result in load_results:
            if load_result['metric'].get('instance') == instance:
                load_value = float(load_result['value'][1])
                break

        uptime_value = None
        for uptime_result in uptime_results:
            if uptime_result['metric'].get('instance') == instance:
                uptime_value = float(uptime_result['value'][1])
                break

        # Add row with collected data
        rows.append({
            "timestamp": current_time,
            "cpu": cpu_value,
            "mem": memory_value,
            "network_receive": network_receive_value,
            "network_transmit": network_transmit_value,
            "disk_read": disk_read_value,
            "disk_write": disk_write_value,
            "disk_usage": disk_usage_value,
            "load": load_value,
            "uptime": uptime_value
        })

    # Transform data into the specified format
    data = {
        "timestamp": [row["timestamp"] for row in rows],
        "cpu": [row["cpu"] for row in rows],
        "mem": [row["mem"] for row in rows],
        "network_receive": [row["network_receive"] for row in rows],
        "network_transmit": [row["network_transmit"] for row in rows],
        "disk_read": [row["disk_read"] for row in rows],
        "disk_write": [row["disk_write"] for row in rows],
        "disk_usage": [row["disk_usage"] for row in rows],
        "load": [row["load"] for row in rows],
        "uptime": [row["uptime"] for row in rows]
    }

    return data

'''

def data_formulation(data_flushed:list, path_to_data_file):
    transformed_data_list = [{key: value[0] for key, value in dic.items()}
    for dic in data_flushed
    ]
        # Check if the file exists to determine if we need to write the header
    file_exists = os.path.isfile(path_to_data_file)

    with open(path_to_data_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=header)

        # Write the header only if the file does not exist or is empty
        if not file_exists:
            writer.writeheader()  # Write header if file does not exist

        # Write all data at once
        writer.writerows(transformed_data_list)

def count_csv_rows(path_to_csv_file):
    # Open the CSV file and count the number of rows
    with open(path_to_csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        # Skip the header row
        next(reader)
        
        # Count the number of rows (excluding the header)
        row_count = sum(1 for row in reader)

    return row_count

def csv_to_dict(path_to_csv_file):

    data = {
        "timestamp": [],
        "cpu": [],
        "mem": [],
        "network_receive":[],
        "network_transmit": [],
        "disk_read": [],
        "disk_write": [],
        "disk_usage": [],
        "load": [],
        "uptime": []
    }

    # Read the CSV and populate the dictionary
    with open(path_to_csv_file, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        
        # Iterate over each row and append the values to the respective lists
        for row in reader:
            data["timestamp"].append(row["timestamp"])
            data["cpu"].append(float(row["cpu"]))  # Convert cpu value to float
            data["mem"].append(float(row["mem"]))  # Convert mem value to float
            data["network_receive"].append(float(row["network_receive"]))
            data["network_transmit"].append(float(row["network_transmit"]))
            data["disk_read"].append(float(row["disk_read"]))
            data["disk_write"].append(float(row["disk_write"]))
            data["disk_usage"].append(float(row["disk_usage"]))
            data["load"].append(float(row["load"]))
            data["uptime"].append(float(row["uptime"]))

    return data   

def clear_csv_content(csv_file):
    # Read the CSV file to get the header
    with open(csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)  # Get the header row

    # Rewrite the CSV file with only the header
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write the header back to the file

    print(f"Content of '{csv_file}' cleared, only header remains.")



def preprocessing(data_flush_list,path_to_data_file):
    data_formulation(data_flush_list,path_to_data_file)
    row_count = count_csv_rows(path_to_data_file)
    if row_count>=30:
        df = pd.DataFrame(csv_to_dict(path_to_data_file))
        clear_csv_content(path_to_data_file)
        print(f"[INFO]: {datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} Batch pre-processing started", flush=True)
        print(df, flush=True)
        
    else:
        print(f"[INFO]: {datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} more lines needed for data preprocessing", flush=True)


'''