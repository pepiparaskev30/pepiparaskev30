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

NODE_NAME = get_node_name()
SAVED_MODELS_PATH = "./saved_models"
WEIGHTS_PATH = "./weights_path"
LOG_PATH_FILE = "./log_path_file"
EVALUATION_PATH = "./evaluation_results"
FEDERATED_WEIGHTS_PATH_SEND_CLIENT = "./federated_send_results"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
evaluation_csv_file = EVALUATION_PATH+"/"+'measurements.csv'

# URLS


logging.basicConfig(filename=LOG_PATH_FILE+"/"+f'info_file_{current_datetime}.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


from kubernetes import client, config

def get_node_ip(node_name):
    try:
        # Load kube config (assumes kubeconfig is set up correctly)
        config.load_kube_config()

        # Create a Kubernetes API client for interacting with nodes
        v1 = client.CoreV1Api()

        # List all nodes in the cluster
        nodes = v1.list_node()

        # Iterate through nodes and find the IP of the desired node
        for node in nodes.items:
            if node.metadata.name == node_name:
                # Iterate through the addresses of the node
                for addr in node.status.addresses:
                    if addr.type == 'InternalIP':
                        return addr.address

        # If the node name is not found or no internal IP is found, return None
        return None

    except Exception as e:
        print(f"Error while retrieving node IP: {e}")
        return None



def check_prometheus_connection(prometheus_url):
    # Define a simple query to test the connection (e.g., the `up` metric)
    query_url = f"{prometheus_url}/api/v1/query"
    params = {
        "query": "up"
    }

    try:
        # Send the GET request to the Prometheus API
        response = requests.get(query_url, params=params, timeout=5)  # Add timeout for safety

        # Check if the response is successful
        if response.status_code == 200:
            print("Connection to Prometheus established successfully.")
            return True
        else:
            print(f"Error: Received status code {response.status_code} from Prometheus.")
            print(response.text)
            return False

    except requests.exceptions.RequestException as e:
        # Handle connection errors
        print(f"Failed to connect to Prometheus: {e}")
        return False


def get_cpu_ts():
    node_name_ip = f"{get_node_ip(NODE_NAME)}:9100"
    # Define the Prometheus server URL and the query
    prometheus_url = f'{PROMETHEUS_URL}:9090/api/v1/query'
    query = '100*avg(1-rate(node_cpu_seconds_total{mode="idle",instance="{}"}[5m])) by (instance)'.format(node_name_ip)

    # URL encode the query to match the query format in the curl request
    encoded_query = urllib.parse.quote(query)

    # Construct the full URL
    url = f'{prometheus_url}?query={encoded_query}'

    # Make the GET request to Prometheus
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Check if the status is success
        if data.get('status') == 'success':
            # Extract the result data
            result = data['data']['result']
            
            # Check if there are any results
            if result:
                # Collect the values and timestamps
                timestamps = []
                values = []
                
                for entry in result:
                    # Each entry contains 'value' as [timestamp, value]
                    timestamp = entry['value'][0]
                    value = float(entry['value'][1])  # Convert value to float
                    
                    timestamps.append(timestamp)
                    values.append(value)
                
                # Normalize the values to the range [0, 1]
                min_value = min(values)
                max_value = max(values)
                
                # Avoid division by zero in case min_value == max_value
                if max_value != min_value:
                    normalized_values = [(v - min_value) / (max_value - min_value) for v in values]
                else:
                    normalized_values = [0] * len(values)  # If all values are the same, normalize to 0
                    
                # Print the timestamp and normalized value
                for ts, norm_val in zip(timestamps, normalized_values):
                    print(f"Timestamp: {ts}, Normalized Value: {norm_val:.4f}")
            else:
                print("No results found for the query.")
        else:
            print("Query failed:", data)
    else:
        print(f"Error: {response.status_code}")



while True:
    print("Node_name", NODE_NAME)
        # Check connection
    print("hello")
    print(get_cpu_ts())
    time.sleep(2)