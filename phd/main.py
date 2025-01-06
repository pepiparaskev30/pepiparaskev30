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
from utilities import retrieve_k8s_information
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
NODE_NAME,SERVICE  = retrieve_k8s_information()

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

QUERY = 'rate(node_cpu_seconds_total[5m])'

while True:
    # Execute the function to run the query every 3 seconds
    print("hello")
    # Perform the HTTP request
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": QUERY})
        response.raise_for_status()  # Raise exception for HTTP errors

        # Parse the JSON response
        result = response.json()
        if result["status"] == "success":
            for metric in result["data"]["result"]:
                print(f"Instance: {metric['metric'].get('instance', 'unknown')}, CPU Usage: {metric['value'][1]}")
        else:
            print(f"Query failed with status: {result['status']} and message: {result.get('error')}")
    except requests.exceptions.RequestException as e:
        print(f"Error querying Prometheus: {e}")
    
    time.sleep(10)

    
