#!/usr/bin/env python
'''
# Maintainer: Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Role: Lead Developer
Copyright (c) 2023 Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
Licensed under the MIT License.
Source code development for the PhD thesis 
Title/Name: main.py 
'''

####################################################################
'''
This is the central script for the entire functionality
'''

import time, os, warnings, json
from datetime import datetime
import pandas as pd
import numpy as np
from requests.api import get
from kubernetes import client, config
import random
from utilities import get_node_name
import logging
import requests
import urllib.parse
from datetime import datetime
import time


################ USEFUL CONSTANT VARIABLES #################
global sequence_length
targets = ["cpu", "mem"]
num_epochs = 20
sequence_length = 2
current_datetime = datetime.now()
early_stopping = {"best_val_loss": float('inf'), "patience" : 5, "no_improvement_count": 0}
iterator = 0
epochs = 10
fisher_multiplier = 1000


trained_model_predictions=[]


################ USEFUL DIRECTORIES #################
global SAVED_MODELS_PATH
global WEIGHTS_PATH
global EVALUATION_PATH
global NODE_NAME

# Define Prometheus server URL
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
NODE_NAME = os.getenv("NODE_NAME")
SAVED_MODELS_PATH = "./saved_models"
WEIGHTS_PATH = "./weights_path"
LOG_PATH_FILE = "./log_path_file"
EVALUATION_PATH = "./evaluation_results"
FEDERATED_WEIGHTS_PATH_SEND_CLIENT = "./federated_send_results"
evaluation_csv_file = EVALUATION_PATH+"/"+'measurements.csv'

logging.basicConfig(filename=LOG_PATH_FILE+"/"+f'info_file_{current_datetime}.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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

    start_time = time.time()
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

# Example usage
if __name__ == "__main__":
    node_name = NODE_NAME # Replace with your actual node name
    while True:
        data = gather_metrics_for_15_seconds(node_name)
        print("\nMetrics Data:")
        print(data)
        time.sleep(3)
