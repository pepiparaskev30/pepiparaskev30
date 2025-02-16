#!/usr/bin/env python
'''
# Maintainer: Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Role: Lead Developer
# Copyright (c) 2023 Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Licensed under the MIT License.
# Source code development for the PhD thesis
# Title/Name: utilities.py
'''
####################################################################
'''
Time-Series Data Collection, Preprocessing, and Causality Detection Pipeline
This script is designed to collect time-series metrics from Prometheus, preprocess the data,
and analyze potential causal relationships between system performance features (CPU, memory, 
network, disk, load, uptime). The following tasks are performed:
#
**Metric Collection**: Gathers metrics (CPU, memory, disk I/O, network traffic, etc.) 
from Prometheus for a given node.
**Preprocessing**: Handles missing values, normalizes data, and performs feature engineering 
(e.g., rate of change for CPU and memory usage).
**Causality Testing**: Uses Granger Causality tests to identify potential causal relationships 
between CPU, memory, and other system metrics.
**Data Storage**: Collects and stores processed metrics into CSV files, with a limit of 30 
data points for batch processing before clearing and preparing for the next cycle.
#
Key Libraries:
- `pandas`, `numpy`: Data manipulation and analysis
- `sklearn`: Machine learning tools, including K-Nearest Neighbors for imputation
- `statsmodels`: Granger causality testing
- `requests`: HTTP requests to Prometheus API
- `kubernetes`: Interaction with Kubernetes API to gather node IP information

Execution flow:
1. Metrics are periodically retrieved via Prometheus queries for system resources.
2. Data is preprocessed to handle missing values, scale numeric features, and generate relevant 
features like "rate of change."
3. Causal relationships are assessed using Granger Causality.
4. Processed data is saved into a CSV file for further analysis or machine learning tasks.

Configuration:
- `PROMETHEUS_URL`: URL of the Prometheus server
- `DATA_GENERATION_PATH`: Path to store collected data (e.g., "./data_generation_path/data.csv")
- `WAIT_TIME`: Time in seconds to wait before collecting new metrics (default is 55 seconds)

'''
# Import necessary libraries
from datetime import datetime
import pandas as pd
import time,os, json
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import numpy as np
import csv
from collections import Counter
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import grangercausalitytests
from contextlib import redirect_stdout
from io import StringIO
import warnings
from kubernetes import client, config
import threading
from queue import Queue
import urllib.parse
import requests
import logging
import tensorflow as tf
from sklearn.impute import SimpleImputer
from LSTM_attention_model_training import DeepNeuralNetwork_Controller, Attention
from elasticweightconsolidation import compute_fisher, ewc_penalty, get_params, update_params
from evaluation_metrics import calculate_mse, calculate_rmse, calculate_r2_score,  save_metrics


############  START logging properties #################
#ignore information messages from terminal
warnings.filterwarnings("ignore")
# Set TensorFlow log level to suppress info messages
tf.get_logger().setLevel('ERROR')
# Configure the logger to filter out the specific message
logger = logging.getLogger('tensorflow')
logger.setLevel(logging.ERROR)
# Suppress the specific message
logger.propagate = False
############ END logging properties #################

#module classes that helps in the pre-processing
label_encoder = LabelEncoder()
scaler = StandardScaler()

# useful variables
global header
header = ["timestamp", "cpu", "mem", "network_receive", "network_transmit",  "load"]

################ USEFUL CONSTANT VARIABLES #################
global sequence_length
global iterator
global trained_model_predictions
trained_model_predictions=[]
targets = ["cpu", "mem"]
num_epochs = 3
sequence_length = 2
current_datetime = datetime.now()
early_stopping = {"best_val_loss": float('inf'), "patience" : 5, "no_improvement_count": 0}
iterator = 0
epochs = 3
fisher_multiplier = 1000
# useful ENV_VARIABLES
NODE_NAME = os.getenv("NODE_NAME")
DATA_GENERATION_PATH = "./data_generation_path/data.csv"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
SAVED_MODELS_PATH = "./saved_models"
WEIGHTS_PATH = "./json_weights"
FEDERATED_WEIGHTS_PATH_RECEIVE = "./federated_received_results"
FEDERATED_WEIGHTS_PATH_SEND_CLIENT = "./federated_send_results"
EVALUATION_PATH = "./evaluation_results"
FEDERATION_URL_SEND = os.getenv("FEDERATION_URL_SEND")
FEDERATION_URL_RECEIVE = "./"

class Gatherer:
    # Flag to check if the threads are ready to collect information
    ready_flag = True
    # Lists to store the results used by CA, RL and GNN
    prometheus_data_queue = Queue()

    # Amount of time to wait before starting a new thread
    wait_time = int(os.getenv('WAIT_TIME', '15'))

    # Start the threads
    def start_thread():
        # Start a CA thread
        threading.Thread(target=Gatherer.flush_data).start()

    # Start a thread and when it finishes, start another one
    def flush_data():
        start_time = time.time()
        N = Gatherer.prometheus_data_queue.qsize()

        data_list = []
        for i in range(N):
            data_list.append(Gatherer.prometheus_data_queue.get())

        Gatherer.ready_flag = False
        preprocessing(data_list, DATA_GENERATION_PATH)
        Gatherer.ready_flag = True

        end_time = time.time()
        sum_time = end_time - start_time

        # If the time is less than the wait time, sleep for the difference
        if sum_time < Gatherer.wait_time:
            time.sleep(Gatherer.wait_time - sum_time)

        # Start a new use_CA thread
        threading.Thread(target=Gatherer.flush_data).start()
        return

# Function to retrieve the internal IP of a node by its name
def get_node_ip_from_name(node_name):
    config.load_incluster_config()  # Load cluster config
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    for address in node.status.addresses:
        if address.type == "InternalIP":
            return address.address
    return None


# Function to query Prometheus metrics
def query_metric(prometheus_url, promql_query):
    # URL-encode the Prometheus query
    encoded_query = urllib.parse.quote(promql_query)
    
    # Construct the full Prometheus API URL
    url = f"{prometheus_url}/api/v1/query?query={encoded_query}"

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

# Function to query Prometheus metrics
def query_metric(prometheus_url, promql_query):
    # URL-encode the Prometheus query
    encoded_query = urllib.parse.quote(promql_query)
    
    # Construct the full Prometheus API URL
    url = f"{prometheus_url}/api/v1/query?query={encoded_query}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return data.get('data', {}).get('result', [])
            else:
                print(f"Query failed: {data.get('error')}", flush=True)
        else:
            print(f"Error: HTTP {response.status_code}, {response.reason}", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}", flush=True)
    return []


def get_memory_usage(node_ip):
    query = f'100 * (node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}} - node_memory_MemAvailable_bytes{{instance="{node_ip}:9100"}}) / node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}}'
    
    # Send the request to Prometheus
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        
        # Extract the result
        result = data['data']['result']
        
        # Check if result is available
        if result:
            value = result[0]['value'][1]  # The second element is the actual value
            return value
        else:
            print(f"No result found for node {node_ip}")
            return 0
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return 0


def get_network_receive_rate(node_ip):
    # Define the Prometheus URL and the query to get network receive rate on eth0
    query = f'rate(node_network_receive_bytes_total{{instance="{node_ip}:9100",device="eth0"}}[1m])'

    # Make the API call to Prometheus
    response = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': query})

    if response.status_code == 200:
        result = response.json()

        # Check if the result contains any data
        if result["status"] == "success" and result["data"]["result"]:
            # Extract the rate value from the result
            value = result["data"]["result"][0]["value"][1]
            return float(value)
        else:
            print(f"No data returned for node {node_ip}", flush=True)
            return 0
    else:
        print(f"Failed to query Prometheus: {response.status_code}", flush=True)
        return 0

def get_network_transmit_rate(node_ip):
    # Define the Prometheus URL and the query to get network transmit rate on eth0
    query = f'rate(node_network_transmit_packets_total{{instance="{node_ip}:9100",device="eth0"}}[1m])'

    # Make the API call to Prometheus
    response = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': query})

    if response.status_code == 200:
        result = response.json()

        # Check if the result contains any data
        if result["status"] == "success" and result["data"]["result"]:
            # Extract the rate value from the result (for eth0 device)
            value = result["data"]["result"][0]["value"][1]
            return float(value)
        else:
            print(f"No data returned for node {node_ip}", flush=True)
            return 0
    else:
        print(f"Failed to query Prometheus: {response.status_code}", flush=True)
        return 0

def get_node_load_average(node_ip):

    # Construct the Prometheus query for node_load1
    query = f'node_load1{{instance="{node_ip}:9100"}}'
    
    # URL for Prometheus API query
    url = f'{PROMETHEUS_URL}/api/v1/query'
    
    # Send GET request to Prometheus API
    response = requests.get(url, params={'query': query})
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        
        # Check if the response contains data
        if data["status"] == "success" and data["data"]["result"]:
            # Extract the value from the result
            load_average = float(data["data"]["result"][0]["value"][1])  # The second value is the load average
            return load_average
        else:
            print(f"No data returned for node {node_ip}.")
            return 0
    else:
        print(f"Failed to fetch data from Prometheus. HTTP Status Code: {response.status_code}")
        return 0


# Function to gather various metrics for 30 seconds
def gather_metrics_for_30_seconds(node_name, prometheus_url=PROMETHEUS_URL):
    # Resolve node IP from node name (assuming a function to resolve node IP)
    node_ip = get_node_ip_from_name(node_name)
    if not node_ip:
        print(f"Could not resolve IP for node: {node_name}")
        return

    # Define the queries with the node's IP
    cpu_query = f'sum(irate(node_cpu_seconds_total{{mode="user",instance="{node_ip}:9100"}}[1m]))'


    rows = []

    # Querying all metrics with 1-second scrape intervals
    cpu_results = query_metric(prometheus_url, cpu_query)
    memory_value = get_memory_usage(node_ip)
    netw_receive_value = get_network_receive_rate(node_ip)
    netw_transmit_value = get_network_transmit_rate(node_ip)
    load_value = get_node_load_average(node_ip)


    # Collect current timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')



    # Extract data from results and associate each metric with the correct instance
    for cpu_result in cpu_results:
        instance = cpu_result['metric'].get('instance', 'unknown')
        cpu_value = float(cpu_result['value'][1])  # The value is a [timestamp, value] pair

        # Add the collected data as a new row
        rows.append({
            "timestamp": current_time,
            "cpu": cpu_value,
            "mem": memory_value, 
            "network_receive": netw_receive_value,
            "network_transmit": netw_transmit_value, 
            "load": load_value

        })

    # Transform data into the specified format
    data = {
        "timestamp": [row["timestamp"] for row in rows],
        "cpu": [row["cpu"] for row in rows],
        "mem": [row["mem"] for row in rows], 
        "network_receive": [row["network_receive"] for row in rows], 
        "network_transmit":[row["network_transmit"] for row in rows],
        "load": [row["load"] for row in rows],
    }
    return data


def data_formulation(data_flushed:list, path_to_data_file):
    transformed_data_list = [{key: value[0] for key, value in dic.items()}
    for dic in data_flushed
    ]
        # Check if the file exists to determine if we need to write the header
    file_exists = os.path.isfile(path_to_data_file)

    with open(path_to_data_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=header)

        # Write the header only if the file does not exist or is empty
        if not file_exists:
            writer.writeheader()  # Write header if file does not exist

        # Write all data at once
        writer.writerows(transformed_data_list)

def count_csv_rows(path_to_csv_file):
    # Open the CSV file and count the number of rows
    with open(path_to_csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        # Skip the header row
        next(reader)
        
        # Count the number of rows (excluding the header)
        row_count = sum(1 for row in reader)

    return row_count

def csv_to_dict(path_to_csv_file):

    data = {
        "timestamp": [],
        "cpu": [],
        "mem": [],
        "network_receive":[],
        "network_transmit": [],
        "load": []
    }

    # Read the CSV and populate the dictionary
    with open(path_to_csv_file, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        
        # Iterate over each row and append the values to the respective lists

        for row in reader:
            data["timestamp"].append(row["timestamp"])
            
            # Check and convert the "cpu" value
            data["cpu"].append(float(row["cpu"]) if row["cpu"] else 0.0)
            
            # Check and convert the "mem" value
            data["mem"].append(float(row["mem"]) if row["mem"] else 0.0)
            
            # Check and convert the "network_receive" value
            data["network_receive"].append(float(row["network_receive"]) if row["network_receive"] else 0.0)
            
            # Check and convert the "network_transmit" value
            data["network_transmit"].append(float(row["network_transmit"]) if row["network_transmit"] else 0.0)
            
            # Check and convert the "load" value
            data["load"].append(float(row["load"]) if row["load"] else 0.0)


    return data   

def load_keras_model(model_path, custom_objects=None):
    """
    Load a Keras model from a .keras file.

    Parameters:
    - model_path (str): Path to the .keras model file.
    - custom_objects (dict): Optional dictionary of custom objects required for deserialization.

    Returns:
    - model (tf.keras.Model): Loaded Keras model.
    """
    try:
        model = tf.keras.models.load_model(model_path, custom_objects=custom_objects)
        print(f"Model loaded successfully from {model_path}.")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None


def init_training_based_on_resource(init_training_, target_resource, early_stopping):
    print(f"[INFO]: Initial Training model for {target_resource}")
    time.sleep(2)
    logging.info(f"Start  the pre-training phase for target {target_resource}")
    training_df = init_training_.df_reformulation(target_metric=target_resource)
    train_x, train_y, validation_x, validation_y = init_training_.train_test_split_(training_df, sequence_length=sequence_length)
    logging.info(f"Start preprocessing training for target {target_resource}")
    model = init_training_.build_model()
    train_model(target_resource, model,train_x,train_y,validation_x, validation_y, num_epochs,early_stopping )
    path_to_model_file = SAVED_MODELS_PATH+"/"+f"model_{target_resource}.keras"
    model.save(path_to_model_file)
    print("saved")

def train_model(target_resource,simple_model, train_x, train_y,validation_x,validation_y, num_epochs,early_stopping):
    mse_list_init, rmse_list_init=[],[]
    for epoch in range(num_epochs):
        logging.info(f"Model started training, is on {epoch+1} epoch")

        simple_model.fit(train_x, train_y, epochs=epoch+1, verbose=1)  # Perform 'epoch+1' epochs of training

        # Validation step
        print("-----------------")
        val_loss = simple_model.evaluate(validation_x, validation_y, verbose=0)
        logging.info(f'Epoch {epoch + 1}, Validation Loss: {val_loss:.4f}')
        print(f'Epoch {epoch + 1}, Validation Loss: {val_loss:.4f}')

        # Check if validation loss has improved
        if val_loss < early_stopping["best_val_loss"]:
            early_stopping["best_val_loss"] = val_loss
            early_stopping["no_improvement_count"] = 0
        else:
            early_stopping["no_improvement_count"] += 1

        # Check if training should stop early
        if early_stopping["no_improvement_count"] >= early_stopping["patience"]:
            logging.info(f'Early stopping after {epoch + 1} epochs.')
            break

    predictions = simple_model.predict(validation_x)
    #print(predictions, flush=True)
    mse = calculate_mse(predictions, validation_y)
    rmse = calculate_rmse(mse)
    r2_score = calculate_r2_score(validation_y, predictions)
    append_to_csv(EVALUATION_PATH, target_resource, mse, rmse, r2_score)
    print("metrics saved...")

    return simple_model

def get_federation_url():
    pass

def federated_learning_send(target_resource, max_retries=100):
    file_to_be_sent = FEDERATED_WEIGHTS_PATH_SEND_CLIENT + "/" + f"{target_resource}_weights_{NODE_NAME}.json"
    create_empty_json_file(file_to_be_sent)
    with open(file_to_be_sent, 'rb') as json_file:
        files = {
            'file': (f'{target_resource}_weights_{NODE_NAME}.json', json_file),
            'target_name': (None, target_resource),
            'node_name': (None, NODE_NAME)
        }

        print("to be sent to the fd master node...", flush=True)
        print(files, flush=True)
        print("-----------------------")
        time.sleep(10)
        response = requests.post(FEDERATION_URL_SEND, files=files)

        retry_count = 0
        while response.status_code != 200 and retry_count < max_retries:
            time.sleep(1)
            print(f"[INFO]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n - MESSAGE: Request is not completed. Retrying...")
            response = requests.post(FEDERATION_URL_SEND, files=files)
            retry_count += 1

        if response.status_code != 200:
            print("[ERROR]: Max retries reached. Request not completed.")

def federated_receive(url, target_resource, max_retries=100, retry_delay=2):
    payload = {"file_type": target_resource}
    print(payload)
    time.sleep(10)
    retries = 0
    while retries < max_retries:
        response = requests.post(url, json= payload)

        if response.status_code == 200:
            try:
                # Try to parse the response as JSON
                
                json_body = response.json()
                if json_body == None:
                    print("[INFO]: weights not ready yet")
                else:
                    print("[INFO]: weights have been received")
                #print("Received JSON body:", json_body)
                return json_body  # Return the JSON body
            except json.JSONDecodeError:
                # Handle the case where the response is not valid JSON
                print("Received non-JSON response. Retrying...")
        else:
            # Handle non-200 status codes
            print(f"Request failed with status code {response.status_code}. Retrying...")

        # Increment the retry count
        retries += 1

        # Introduce a delay before making the next request
        time.sleep(retry_delay)

    print(f"Maximum retries ({max_retries}) reached. No valid JSON response received.")
    return None

def write_json_body(file_path, json_data):
    # Write the JSON object to the file
    with open(file_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)

    print(f"The JSON data has been successfully written to {file_path}.")

def calculate_rate_of_change(lst):
    rates = [lst[i] - lst[i - 1] for i in range(1, len(lst))]
    return rates

def analyze_rate_of_change(rates):
    positive_rates = sum(rate > 0 for rate in rates)
    negative_rates = sum(rate < 0 for rate in rates)

    if positive_rates > negative_rates:
        return 1
    elif positive_rates < negative_rates:
        return -1
    else:
        return 0

def trend_of_values(lst):
    increasing = all(lst[i] < lst[i + 1] for i in range(len(lst) - 1))
    decreasing = all(lst[i] > lst[i + 1] for i in range(len(lst) - 1))

    if increasing:
        return 1
    elif decreasing:
        return -1
    else:
        return 0

def calculate_convergence(path_, target):
    data_list, mse_list, rmse_list, r2_list = [],[],[],[]
    for file_ in os.listdir(path_):
        if file_.endswith(f"{target}.csv"):
            with open(path_+"/"+file_, "r") as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    data_list.append(row)
                for element in data_list:
                    for k,v in element.items():
                        if k == "MSE":
                            mse_list.append(float(v))
                        elif k =="RMSE": 
                            rmse_list.append(float(v))
                        else:
                            r2_list.append(float(v))

                trend_mse, trend_rmse, trend_r2 = trend_of_values(mse_list), trend_of_values(rmse_list), trend_of_values(r2_list)
                return trend_mse, trend_rmse, trend_r2

                
        else:
            continue


def count_frequency(tuple_):
    # Use Counter to count occurrences of each value
    value_counts = Counter(tuple_)

    # Find the maximum frequency
    max_frequency = max(value_counts.values())

    # Find all values with the maximum frequency
    most_frequent_values = [value for value, frequency in value_counts.items() if frequency == max_frequency]

    return most_frequent_values

def clear_csv_content(csv_file):
    # Read the CSV file to get the header
    with open(csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)  # Get the header row

    # Rewrite the CSV file with only the header
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write the header back to the file

    print(f"Content of '{csv_file}' cleared, only header remains.")

def preprocessing(data_flush_list,path_to_data_file, iterator=0):
    print(data_flush_list, flush=True)
    data_formulation(data_flush_list,path_to_data_file)
    row_count = count_csv_rows(path_to_data_file)
    if row_count>=15:
        df = pd.DataFrame(csv_to_dict(path_to_data_file))
        for i in range(0,3):
            print(i, flush=True)
            if  iterator == 0:
                updated_df, causality_cpu, causalilty_ram=preprocess_time_series_data(df)
                features_cpu, features_ram =find_resource_features(causality_cpu, causalilty_ram, updated_df)
                features_cpu =['mem', "network_receive", "network_transmit", "load"]
                features_ram = ['cpu',"network_receive", "network_transmit", "load"]
                init_training_ = DeepNeuralNetwork_Controller(df, features_cpu, features_ram)
                for target_resource in targets:
                    init_training_based_on_resource(init_training_, target_resource, early_stopping)
                    print("Initial training completed", flush=True)

            elif iterator>=1:
                print("Incremental procedure started", flush=True)
                updated_df, causality_cpu, causalilty_ram=preprocess_time_series_data(df)
                incremental_training_ = DeepNeuralNetwork_Controller(updated_df, features_cpu, features_ram)
                for target_resource in targets:
                    iterator_, target_resource, predictions_= incremental_training(incremental_training_,target_resource, iterator)
                    if i%2==0:
                        print(f"========== predictions for {target_resource} ==========")
                        predictions_final_ = predictions_.tolist()
                        for element in predictions_final_:
                            trained_model_predictions.append(element[0])
                        result = analyze_rate_of_change(calculate_rate_of_change(trained_model_predictions))
                        print(result)
                        time.sleep(10)
                        if result in (0,1):
                            pass
                        else: 
                            print("trigger re-adaptation")
                            time.sleep(1000)



                        predictions_final_=[]


                        time.sleep(10)
                    metrics_convergence = calculate_convergence(EVALUATION_PATH, target_resource)
                    most_frequent_value = count_frequency(metrics_convergence)
                    if len(most_frequent_value) == 1:
                        if most_frequent_value[0] == 1:
                            pass
                        else:
                            print("Welcome to Federated Learning!!", flush=True)
                            time.sleep(1)
                            federated_learning_send(target_resource)
                            print("wait now!!!", flush=True)
                            while True:
                                federated_weights = federated_receive(FEDERATION_URL_RECEIVE, target_resource=target_resource)
                                
                                if federated_weights != None:
                                    print(f"[INFO]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n MESSAGE: Aggregated weights have been received")
                                    time.sleep(2)
                                    break
                                else:
                                    print(f"[INFO]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n MESSAGE: Aggregated weights have not been received yet")
                                    time.sleep(2)
                            write_json_body(f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_aggregated.json", federated_weights)     

                            
                    else:
                        print("Welcome to \n Federated Learning!!")
                        time.sleep(1)
                        federated_learning_send(target_resource) 
                        federated_receive(FEDERATION_URL_RECEIVE)
                        while True:
                            federated_weights = federated_receive(FEDERATION_URL_RECEIVE)
                            if federated_weights != None:
                                print(f"[INFO]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n MESSAGE: Aggregated weights have been received")
                                time.sleep(2)
                                break
                            else:
                                print(f"[INFO]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n MESSAGE: Aggregated weights have not been received yet")
                                time.sleep(2)
                        
                        write_json_body(f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_{NODE_NAME}_aggregated.json", federated_weights)     

            iterator+=1        
        i = 0
        time.sleep(4)


        clear_csv_content(path_to_data_file)
        print(f"[INFO]: {datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} Batch pre-processing started", flush=True)
        print(df, flush=True)
        
    else:
        print(f"[INFO]: {datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} more lines needed for data preprocessing", flush=True)

def create_empty_json_file(filepath):
    """
    Creates an empty JSON file at the specified filepath.

    Args:
        filepath (str): The path to the JSON file to be created.
    """
    try:
        # Check if the file already exists
        if not os.path.exists(filepath):
            # Create an empty dictionary
            empty_data = {}

            # Open the file in write mode ('w')
            with open(filepath, 'w') as json_file:
                # Use json.dump() to write the empty dictionary to the file
                json.dump(empty_data, json_file, indent=4)  # indent for readability

            print(f"Empty JSON file created successfully at: {filepath}")
        else:
            print(f"File already exists at: {filepath}")

    except Exception as e:
        print(f"An error occurred: {e}")

def find_resource_features(causality_cpu, causality_ram, updated_df:pd.DataFrame):
    if len(causality_cpu) == 0:
        cpu_to_remove = ["cpu", "timestamp"]
        features_cpu = [item for item in list(updated_df.columns) if item not in cpu_to_remove]
    else:
        features_cpu = causality_cpu
    if len(causality_ram) == 0:
        ram_to_remove = ["mem", "timestamp"]
        features_ram = [item for item in list(updated_df.columns) if item not in ram_to_remove]
    else:
        features_ram = causality_ram
    
    return features_cpu, features_ram

def incremental_training(incremental_training_, target_resource, iterator):
    print("============ INCREMENTAL PROCEDURE =======================", flush=True)

    # Load old model and obtain its weights
    old_model_file = SAVED_MODELS_PATH + "/" + "model_" + target_resource + ".keras"
    training_incremental_df = incremental_training_.df_reformulation(target_resource)
    train_x, train_y, validation_x, validation_y = incremental_training_.train_test_split_(training_incremental_df, sequence_length)

    # Load the old model and apply weights
    incremental_model = load_keras_model(old_model_file, custom_objects={'Attention': Attention})
    weights_file = WEIGHTS_PATH + "/" + f"{target_resource}_weights_{NODE_NAME}.weights.h5"
    incremental_model.save_weights(weights_file)
    print("weights saved", flush=True)
    time.sleep(10)
    logging.info(f"model: {incremental_model} loaded")

    # Apply federated weights if they exist
    if len(os.listdir(FEDERATED_WEIGHTS_PATH_RECEIVE)) != 0 and len(os.listdir(FEDERATED_WEIGHTS_PATH_RECEIVE)) == 1:
        if file_contains_word(FEDERATED_WEIGHTS_PATH_RECEIVE, target_resource):
            incremental_model = update_model_with_federated_weights(incremental_model, target_resource)

    # Create dataset, set drop_remainder=True to ensure batch consistency
    dataset_current_task = tf.data.Dataset.from_tensor_slices((train_x, train_y)).batch(32, drop_remainder=True)

    # Optimizer for training
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.01)

    # Store the initial parameters
    prev_params = get_params(incremental_model)

    # Calculate steps per epoch (number of batches)
    steps_per_epoch = len(train_x) // 32  # Ensure the steps match the dataset size

    for epoch in range(epochs):
        batch_count = 0
        try:
            for data, target in dataset_current_task:
                # Ensure data has a batch dimension if it's missing
                if len(data.shape) == 2:  # if shape is (2, 12), expand to (1, 2, 12)
                    data = tf.expand_dims(data, axis=0)

                # Gradient calculation
                with tf.GradientTape() as tape:
                    output = incremental_model(data)
                    loss = tf.keras.losses.mean_squared_error(target, output)
                    fisher = compute_fisher(incremental_model, dataset_current_task)
                    ewc_loss = loss + ewc_penalty(get_params(incremental_model), prev_params, fisher, fisher_multiplier)

                grads = tape.gradient(ewc_loss, incremental_model.trainable_variables)
                optimizer.apply_gradients(zip(grads, incremental_model.trainable_variables))

                batch_count += 1
                if batch_count >= steps_per_epoch:
                    break  # Stop after processing the expected number of batches

        except tf.errors.OutOfRangeError:
            print(f"End of dataset reached for epoch {epoch + 1}")

        # Update the previous parameters for the next iteration
        prev_params = update_params(incremental_model, prev_params)

    # Save the model and weights after fine-tuning
    #incremental_model.save_weights(WEIGHTS_PATH + "/" + f"{target_resource}_weights_{NODE_NAME}.h5")
    incremental_model.save_weights(WEIGHTS_PATH + "/" + f"{target_resource}_weights_{NODE_NAME}.weights.h5")

    incremental_model.save(SAVED_MODELS_PATH + "/" + f"model__{target_resource}.keras")
    weights_list = [arr.tolist() for arr in incremental_model.get_weights()]

    # Save the model weights to a JSON file for federated learning
    json_filepath = f"{FEDERATED_WEIGHTS_PATH_SEND_CLIENT}/{target_resource}_weights_{NODE_NAME}.json"
    save_weights_to_json(weights_list, json_filepath)

    logging.info(f"fine-tuned model: fine_tuned_model model_{target_resource}.keras saved")
    logging.info(f"and the weights: fine_tuned_model_weights_{target_resource}.h5 saved")
    logging.info(f"and the weights: fine_tuned_model_weights_{target_resource}.json saved")

    # Perform validation and predictions
    validation_data = (validation_x, validation_y)
    predictions = incremental_model.predict(validation_data[0])

    # Calculate performance metrics
    mse = calculate_mse(predictions, validation_data[1])
    rmse = calculate_rmse(mse)
    r2_score = calculate_r2_score(validation_data[1], predictions)

    # Log and save the metrics
    append_to_csv(EVALUATION_PATH, target_resource, mse, rmse, r2_score)
    print("metrics exposed, incremental model and fine-tuned weights saved")

    return iterator, target_resource, predictions


def append_to_csv(EVALUATION_PATH,target,mse, rmse, r2):
    file_path = EVALUATION_PATH+"/"+f"metrics_{target}.csv"
    with open(file_path, 'a', newline='') as csvfile:
        fieldnames = ['MSE', 'RMSE', 'R2']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If the file is empty, write the header
        if csvfile.tell() == 0:
            writer.writeheader()

        # Append the metrics
        writer.writerow({'MSE': mse, 'RMSE': rmse, 'R2': r2})

def save_weights_to_json(weights_list:list, json_file_path: str):
    """
    Save the weights of a Keras model to a JSON file.

    Parameters:
    - model: A Keras model.
    - json_file_path: The file path to save the JSON file.
    """
    # Get the weights from the model
    #weights_list = [arr.tolist() for arr in model.get_weights()]

    # Convert to JSON string
    weights_json = json.dumps(weights_list)

def file_contains_word(path_, word):
    """
    Returns:
    - bool: True/False if the file's name contains the word
    """
    for element in os.listdir(path_):
        file_name = os.path.basename(path_+element)  # Extract the file name from the file path

    return word in file_name

def delete_file(file_name):
    try:
        # Check if the file exists
        if os.path.exists(file_name):
            # Delete the file
            os.remove(file_name)
            print(f"The file '{file_name}' has been successfully deleted.")
        else:
            print(f"The file '{file_name}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def update_model_with_federated_weights(loaded_model, target_resource):
    ### this is important code
    # Load weights from JSON file
    with open(f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_aggregated.json", 'r') as json_file:
        weights_data = json.load(json_file)
    # Iterate through layers in the model
    for layer in loaded_model.layers:
        # Check if the layer has weights in your JSON
        if layer.name in weights_data:
            # Load weights from JSON and set them to the layer
            layer.set_weights([np.array(weights_data[layer.name][param]) for param in layer.trainable_weights])
    
    delete_file(f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_aggregated.json")
    return loaded_model

#custom made function to apply k-nn in missing-value ts columns
def k_nearest_neighbors(df:pd.DataFrame, col_):
    k_neighbors = 3
    knn = KNeighborsRegressor(n_neighbors=k_neighbors)

    # Split the DataFrame into known and missing values
    known_values = df.dropna(subset=[col_])
    missing_values = df[df[col_].isna()]
    # Fit the KNeighborsRegressor on known values
    knn.fit(known_values.drop(columns=[col_]), known_values[col_])
    # Interpolate missing values
    interpolated_values = knn.predict(missing_values.drop(columns=[col_]))
    # Fill in the missing values with the interpolated values
    df.loc[df[col_].isna(), col_] = interpolated_values

    return df

class DataPipeline:
    '''
    A class representing a data processing pipeline that includes various preprocessing steps.
    Also this class is dedicated to preparing time-series data for machine/deep learning tasks.
    
    Specifically includes:
    - Missing values imputation:  Identify and handle missing data points.
    -Scaling and Standardization: Normalize or standardize the data as required.
    -Granger Causality Testing: Perform Granger causality tests to determine if the potential causal variable can predict or cause changes in the response variable.
    -Feature Engineering: Engineer relevant features, including lag features for the potential causal variable.
    -Label Encoding: To convert categorical variables into numerical values. 

    '''

    def __init__(self, df:pd.DataFrame):
        self.df = df
        self.columns = list(df.columns)
        self.str_columns=list(df.select_dtypes(include=['object']).columns)
        self.float_columns = list(df.select_dtypes(include=['float64']).columns)
        self.int_columns = list(df.select_dtypes(include=['int64']).columns)
        self.features_with_trend = []

    def adjust_columns(self):
        self.columns = list(self.df.columns)
        self.str_columns=list(self.df.select_dtypes(include=['object']).columns)
        self.float_columns = list(self.df.select_dtypes(include=['float64']).columns)
        self.int_columns = list(self.df.select_dtypes(include=['int64']).columns)
        self.features_with_trend = []

    def missing_values(self):
        threshold = 0.75
        '''
        ## Module to clean the data from missing values:
        '''
        if self.str_columns != None:

            for col in self.str_columns:
                if self.df[col].isna().mean() == 0.0:
                    pass
                    #print(f"[INFO]: {col}, no missing values")

                else:
                    if self.df[col].isna().mean()>threshold:
                        #print(f"[INFO]: {col} has up to {threshold*100}% missing values, the entire column will be removed")
                        self.df.drop(columns=col, inplace=True)
                    else:
                        #print(f"[INFO]: {col} has lower than {threshold*100}% missing values, we will impute the missing values")
                        self.df[col] = self.df[col].fillna(-999)
        else:
            pass

        if self.float_columns != None:
            for col in self.float_columns:
                if self.df[col].isna().mean()==0.0:
                    pass
                    
                    #print(f"[INFO]: {col}, no missing values")

                else:
                    if self.df[col].isna().mean()>threshold:
                        #print(f"[INFO]: {col} has up to {threshold*100}% missing values, the entire column will be removed")
                        self.df.drop(columns=col, inplace=True)

                    else:
                        #print(f"[INFO]: {col} has lower than {threshold*100}% missing values, we will impute the missing values")
                        k_nearest_neighbors(self.df, col)
                    
        else:
            pass


        if self.int_columns!= None:
            ##to be tested for int value columns
            for col in self.int_columns:
                if self.df[col].isna().mean() == 0.0:
                    pass
                    #print(f"[INFO]: {col}, no missing values")


                else:
                    if self.df[col].isna().mean()>threshold:
                        #print(f"[INFO]: {col} has up to {threshold*100}% missing values, the entire column will be removed")
                        self.df.drop(columns=col, inplace=True)

                    else:
                        print(f"[INFO]: {col} has lower than {threshold*100}% missing values, we will impute the missing values")
                        k_nearest_neighbors(self.df, col)
        else:
            pass

    
    def normalization(self):
        self.adjust_columns()
        '''
        This function is responsible for normalizing float values
        '''
        for col in self.columns:
            if col !="timestamp":
                self.df[col] = scaler.fit_transform(self.df[col].values.reshape(-1, 1))
            else:
                pass
    
    def feature_engineering(self, column_name):
        self.adjust_columns()
        """
        Feature Engineering for Predictive Modeling

        This function performs feature engineering on a dataset to prepare it for predictive modeling tasks. 
        Feature engineering is a crucial step in data preprocessing that involves creating, transforming, or selecting features to improve model performance.
        
        Speficially this function performs:
        - Feature creation: Generates new features by combining or transforming existing features.
 
        """

        idx=self.df.columns.get_loc(column_name)
        idx_col = str(idx)
        if column_name =="cpu":
            cpu_values = list(self.df[column_name].values)
            rate_of_change_cpu = [x - cpu_values[i - 1] for i, x in enumerate(cpu_values)][1:]
            final_rate_of_change_cpu = [0]
            for element in rate_of_change_cpu:
                final_rate_of_change_cpu.append(element)
            self.df.insert(loc=idx+1, column='cpu_rate_of_change', value=final_rate_of_change_cpu)
        elif column_name=="mem":
            ram_values = list(self.df[column_name].values)
            rate_of_change_ram = [x - ram_values[i - 1] for i, x in enumerate(ram_values)][1:]
            final_rate_of_change_ram = [0]
            for element in rate_of_change_ram:
                final_rate_of_change_ram.append(element)
            self.df.insert(loc=idx+1, column='memory_rate_of_change', value=final_rate_of_change_ram)
    

    def get_causality(self, column_name):
        if column_name == "cpu":
            return ["mem", "network_receive", "network_transmit",  "load"]
        else:
            return ["cpu", "network_receive", "network_transmit",  "load"]

    
    def erase_rate_of_change_metrics(self):
        '''
        Function helping to clean some past values (strongly connected with feature_engineering method)
        '''
        del(self.df['cpu_rate_of_change'])
        del(self.df['memory_rate_of_change'])

    
def preprocess_time_series_data(df:pd.DataFrame):
    '''
    Main function to perform all the pre-processing steps following a specific order
    '''
    pipeline = DataPipeline(df)
    print("Data inserted, pre-processing process is initialized")
    time.sleep(1)
    print("1. Missing values detection and imputation", flush=True)
    print("===========================================")
    pipeline.missing_values()
    print("===========================================")
    print("2. Feature engineering", flush=True)
    print("===========================================")
    time.sleep(1)
    pipeline.feature_engineering("cpu")
    pipeline.feature_engineering("mem")
    print("3. Normalization",flush=True)
    print("===========================================")
    time.sleep(1)
    pipeline.normalization()
    causality_cpu = pipeline.get_causality(column_name="cpu")
    causality_ram  = pipeline.get_causality(column_name="mem")
    #dict_data= pipeline.df.to_dict(orient='list')
    pipeline.erase_rate_of_change_metrics()

    # Print the JSON data
    return pipeline.df,causality_cpu, causality_ram



    