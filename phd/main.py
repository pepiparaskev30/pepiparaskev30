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



# Ensure PROMETHEUS_URL is defined globally or passed as a parameter

# Define Prometheus server URL
PROMETHEUS_URL = "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"

def query_cpu_user_mode():
    # PromQL query
    query = '100 * avg(rate(node_cpu_seconds_total{mode="user"}[5m])) by (instance)'
    
    # URL encode the query
    encoded_query = urllib.parse.quote(query)
    
    # Construct the full query URL
    url = f"{PROMETHEUS_URL}/api/v1/query?query={encoded_query}"
    
    try:
        # Make the GET request to Prometheus
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Check if the query was successful
            if data.get('status') == 'success':
                results = data.get('data', {}).get('result', [])
                
                # Print the results
                for result in results:
                    instance = result['metric'].get('instance', 'unknown')
                    value = float(result['value'][1])  # The value is a [timestamp, value] pair
                    print(f"Instance: {instance}, User CPU Usage (%): {value:.2f}")
            else:
                print(f"Query failed: {data.get('error')}")
        else:
            print(f"Error: HTTP {response.status_code}, {response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")



while True:
    print("Node_name", NODE_NAME)
        # Check connection
    print("hello")
    print(query_cpu_user_mode())
    time.sleep(2)