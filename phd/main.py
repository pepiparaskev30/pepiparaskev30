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
from kubernetes import client, config
import logging
from datetime import datetime
import time
import time
import socket
import json



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
timestamp_list, cpu_list, mem_list = [], [], []
logging.basicConfig(filename=LOG_PATH_FILE+"/"+f'info_file_{current_datetime}.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

resource_dictionaries = [{'timestamp': ['2025-01-27 08:32:43'], 'cpu': [4.2921296296279055], 'mem': [34.5519825762939]}, {'timestamp': ['2025-01-27 08:32:58'], 'cpu': [4.2921296296279055], 'mem': [34.5519825762939]}]


for resource_dictionary in resource_dictionaries:
    for k, v in resource_dictionary.items():
        if k == "timestamp":
            timestamp_list.append(v[0])
        if k == "cpu":
            cpu_list.append(v[0])
        if k == "mem":
            mem_list.append(v[0])
data = {"timestamp":timestamp_list, "cpu": cpu_list, "mem": mem_list}



