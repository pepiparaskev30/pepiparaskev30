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



# Define Prometheus server URL
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")

def query_metric(promql_query):
    # URL encode the query
    encoded_query = urllib.parse.quote(promql_query)

    # Construct the full query URL
    url = f"{PROMETHEUS_URL}/api/v1/query?query={encoded_query}"

    try:
        # Make the GET request to Prometheus
        response = requests.get(url, timeout=10)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()

            # Check if the query was successful
            if data.get('status') == 'success':
                return data.get('data', {}).get('result', [])
            else:
                print(f"Query failed: {data.get('error')}")
        else:
            print(f"Error: HTTP {response.status_code}, {response.reason}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

    return []

def gather_metrics_for_10_seconds():
    cpu_query = '100 * avg(rate(node_cpu_seconds_total{mode="user"}[5m])) by (instance)'
    memory_query = '100 * (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes'

    start_time = time.time()
    rows = []

    while time.time() - start_time < 10:
        # Query CPU usage
        cpu_results = query_metric(cpu_query)

        # Query Memory usage
        memory_results = query_metric(memory_query)

        # Collect current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Collect CPU usage results
        for result in cpu_results:
            instance = result['metric'].get('instance', 'unknown')
            cpu_value = float(result['value'][1])  # The value is a [timestamp, value] pair
            rows.append({
                'timestamp': current_time,
                'instance': instance,
                'metric': 'cpu_usage',
                'value': cpu_value
            })

        # Collect Memory usage results
        for result in memory_results:
            instance = result['metric'].get('instance', 'unknown')
            memory_value = float(result['value'][1])  # The value is a [timestamp, value] pair
            rows.append({
                'timestamp': current_time,
                'instance': instance,
                'metric': 'memory_usage',
                'value': memory_value
            })

        # Sleep briefly to avoid excessive requests
        time.sleep(1)

    # Create a pandas DataFrame
    df = pd.DataFrame(rows)
    return df

# Example usage
if __name__ == "__main__":
    while True:
        df = gather_metrics_for_10_seconds()
        if df is not None:
            print("\nMetrics DataFrame:")
            print(df)
        time.sleep(3)
