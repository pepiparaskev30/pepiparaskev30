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

from multiprocessing import Queue
import time


def data_processor(queue):
    print("Data Processor started...")

    while True:
        # Check if data is available
        if not queue.empty():
            data_batch = queue.get()  # Retrieve data from the queue
            print(f"Processing data batch: {data_batch}")

            # Simulate data pre-processing
            time.sleep(10)  # Simulate pre-processing time

            print("Finished processing data batch.\n")
        else:
            print("Waiting for new data...")
            time.sleep(2)  # Short wait before checking again


if __name__ == "__main__":
    data_queue = Queue()  # Shared queue for inter-process communication

    # Start the Data Processor process
    data_processor(data_queue)

