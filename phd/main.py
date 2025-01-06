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

def get_node_cpu_usage(prometheus_url, node_name):
    # Define the PromQL query to get the CPU usage of the specified node
    promql_query = f"""
    100 - (avg by(instance) (rate(node_cpu_seconds_total{{mode="idle", instance=~"{node_name}.*"}}[5m])) * 100)
    """

    # Define the Prometheus API URL for querying
    query_url = f"{prometheus_url}/api/v1/query"

    # Define the parameters for the request
    params = {
        "query": promql_query
    }

    try:
        # Send the GET request to Prometheus API
        response = requests.get(query_url, params=params)

        # Check if the response is successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            # Extract the CPU usage value from the response
            if "data" in data and "result" in data["data"] and len(data["data"]["result"]) > 0:
                cpu_usage = data["data"]["result"][0]["value"][1]
                return float(cpu_usage)
            else:
                print("No data returned from Prometheus.")
                return None
        else:
            print(f"Error: Received status code {response.status_code} from Prometheus.")
            print(response.text)
            return None

    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return None

if __name__ == "__main__":
    print("Node_name", NODE_NAME)
    print(get_node_cpu_usage(NODE_NAME, PROMETHEUS_URL))
    time.sleep(2)
