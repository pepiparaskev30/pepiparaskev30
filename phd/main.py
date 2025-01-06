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
NODE_NAME = get_node_name()

################ USEFUL DIRECTORIES #################
global SAVED_MODELS_PATH
global WEIGHTS_PATH
global EVALUATION_PATH

SAVED_MODELS_PATH = "./saved_models"
WEIGHTS_PATH = "./weights_path"
LOG_PATH_FILE = "./log_path_file"
EVALUATION_PATH = "./evaluation_results"
FEDERATED_WEIGHTS_PATH_SEND_CLIENT = "./federated_send_results"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
evaluation_csv_file = EVALUATION_PATH+"/"+'measurements.csv'

# URLS


logging.basicConfig(filename=LOG_PATH_FILE+"/"+f'info_file_{current_datetime}.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def get_cpu_usage_for_node(prometheus_url, node_name):
    """
    Queries Prometheus for CPU usage for a specific node using Node Exporter metrics.
    
    Args:
        prometheus_url (str): URL of the Prometheus server.
        node_name (str): The name of the node to query (matches the `instance` label in Prometheus).
    
    Returns:
        float: The CPU usage percentage for the specified node, or None if not found.
    """
    # Define the PromQL query for the specific node
    promql_query = f"""
    100 - (avg by (instance) (rate(node_cpu_seconds_total{{mode="idle", instance="{node_name}"}}[5m])) * 100)
    """
    
    # Define the Prometheus API query URL
    query_url = f"{prometheus_url}/api/v1/query"
    
    # Set query parameters
    params = {
        "query": promql_query
    }

    try:
        # Send the GET request to the Prometheus API
        response = requests.get(query_url, params=params, timeout=10)

        # Check if the response is successful
        if response.status_code == 200:
            data = response.json()

            # Extract the CPU usage value for the specified node
            if "data" in data and "result" in data["data"] and len(data["data"]["result"]) > 0:
                cpu_usage = float(data["data"]["result"][0]["value"][1])  # Value is [timestamp, value]
                return cpu_usage
            else:
                print(f"No data returned for node '{node_name}'.")
                return None
        else:
            print(f"Error: Received status code {response.status_code} from Prometheus.")
            print(response.text)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Failed to query Prometheus: {e}")
        return None


while True:
    print("Node_name", NODE_NAME)
        # Check connection
    print("hello")
    print(get_cpu_usage_for_node(PROMETHEUS_URL, NODE_NAME))
    time.sleep(2)