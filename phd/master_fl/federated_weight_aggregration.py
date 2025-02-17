#!/usr/bin/env python
'''
# Script: fed_master.py
# Maintainer: Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Role: Lead Developer
# Copyright (c) 2025 Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Licensed under the MIT License.
# Source code development for the PhD thesis 

####################################################################
# Overview:

This code will reside on the master node where the aggregation of the node pre-
trained model weights will be utilized.

The script checks if more than one node has sent its weights and if so, it performs
aggregation. Then the aggregated weights are saved in the specific directory to be retrived by
the nodes (via a GET API)

'''

import os, json, time
import numpy as np

from utilities import delete_files_in_folder
from datetime import datetime
from utilities import delete_file, count_files_with_word, list_files_with_word

red_color_code = "\033[91m"
blue_color_code = "\033[94m"
reset_color_code = "\033[0m"

#global MASTER_WEIGHTS_RECEIVE
global FEDERATED_WEIGHTS_PATH_SEND
global AGGREGATED_JSON_FILES
global NODE_NOTBOOK_DIR


MASTER_WEIGHTS_PATH_RECEIVE = "./master_received_weights_json"
FEDERATED_WEIGHTS_PATH_SEND = "./federated_send_results"
AGGREGATED_JSON_FILES = "./aggregated_json_files"
NODE_NOTBOOK_DIR = "./nodes_notebook"


json_cpu_files_list = []
json_mem_files_list = []
def file_contains_word(path_, word):
    """
    Returns:
    - bool: True/False if the file's name contains the word
    """
    for element in os.listdir(path_):
        file_name = os.path.basename(path_+element)  # Extract the file name from the file path

    return word in file_name

def aggregate_weights_json(json_file_paths,target_resource):
    '''
    Function that receives the list with each resource node weights (in json format)
    and creates an aggregated json file that is stored in AGGREGATED_JSON_FILES path
    '''
    aggregated_weights = None

    # Iterate through each JSON file
    for json_file_path in json_file_paths:
        with open(json_file_path, 'r') as json_file:
            loaded_weights_jsonable = json.load(json_file)

        # Convert the loaded weights back to NumPy arrays
        loaded_weights = [np.array(arr) for arr in loaded_weights_jsonable]

        # Initialize or update the aggregated weights
        if aggregated_weights is None:
            aggregated_weights = loaded_weights
        else:
            aggregated_weights = [aggregated + current for aggregated, current in zip(aggregated_weights, loaded_weights)]

    # Convert the aggregated weights to lists for JSON serialization
    aggregated_weights_jsonable = [arr.tolist() for arr in aggregated_weights]

    # Save the aggregated weights to a new JSON file
    with open(f'{AGGREGATED_JSON_FILES}/{target_resource}_weights_aggregated.json', 'w') as output_json_file:
        json.dump(aggregated_weights_jsonable, output_json_file, indent=2)

    print(f"{blue_color_code}[INFO] {reset_color_code} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n MESSAGE:Aggregated weights saved to {AGGREGATED_JSON_FILES}/{target_resource}_weights_aggregated.json")



while True:
    while True:

        while len(os.listdir(MASTER_WEIGHTS_PATH_RECEIVE))<=1:
            print(" ")
            print(f"{red_color_code}[INFO]:{reset_color_code} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n MESSAGE: {len(os.listdir(MASTER_WEIGHTS_PATH_RECEIVE))} nodes weights have been loaded, need for more")
            time.sleep(5)
        break


    time.sleep(2)
    
    if count_files_with_word(MASTER_WEIGHTS_PATH_RECEIVE, "cpu") >1:
        list_cpu_files = [os.path.join(MASTER_WEIGHTS_PATH_RECEIVE, file_name) for file_name in list_files_with_word(MASTER_WEIGHTS_PATH_RECEIVE, "cpu")]
        aggregate_weights_json(list_cpu_files, target_resource="cpu")
        for element in list_cpu_files:
            delete_file(element)


    else:
        pass

    if count_files_with_word(MASTER_WEIGHTS_PATH_RECEIVE, "mem") >1:
        list_mem_files  = [os.path.join(MASTER_WEIGHTS_PATH_RECEIVE, file_name) for file_name in list_files_with_word(MASTER_WEIGHTS_PATH_RECEIVE, "mem")]
        aggregate_weights_json(list_mem_files, target_resource="mem")
        for element in list_mem_files:
            delete_file(element)
    else:
        pass

    time.sleep(3)






    



