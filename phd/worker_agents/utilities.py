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
import psutil
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
import os


############  START logging properties #################
warnings.filterwarnings("ignore")
tf.get_logger().setLevel('ERROR')
logger = logging.getLogger('tensorflow')
logger.setLevel(logging.ERROR)
logger.propagate = False
############ END logging properties #################

label_encoder = LabelEncoder()
scaler = StandardScaler()

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
FEDERATION_URL_RECEIVE = os.getenv("FEDERATION_URL_RECEIVE")


BATCH_SIZE = 32
MAX_STEPS_PER_EPOCH = 5        # at most 5 batches per epoch
MAX_FISHER_BATCHES = 3         # at most 3 batches to estimate Fisher
MIN_SAMPLES_FOR_TRAIN = 32     # don't train if less than one full batch


class Gatherer:
    # Flag to check if the threads are ready to collect information
    ready_flag = True
    # Lists to store the results used by CA, RL and GNN
    prometheus_data_queue = Queue()

    # Amount of time to wait before starting a new thread
    wait_time = int(os.getenv('WAIT_TIME', '15'))

    # Start the threads
    def start_thread():
        threading.Thread(target=Gatherer.flush_data).start()

    # Start a thread and when it finishes, start another one
    def flush_data():
        global iterator
        start_time = time.time()
        N = Gatherer.prometheus_data_queue.qsize()

        data_list = []
        for i in range(N):
            data_list.append(Gatherer.prometheus_data_queue.get())

        Gatherer.ready_flag = False
        iterator = preprocessing(data_list, DATA_GENERATION_PATH, iterator)
        Gatherer.ready_flag = True

        end_time = time.time()
        sum_time = end_time - start_time

        if sum_time < Gatherer.wait_time:
            time.sleep(Gatherer.wait_time - sum_time)

        threading.Thread(target=Gatherer.flush_data).start()
        return

def append_latency_to_csv(evaluation_path, target, phase, latency_seconds):
    """
    Append incremental inference latency to a CSV file.
    """
    file_path = os.path.join(evaluation_path, f"latency_{target}.csv")
    fieldnames = ["timestamp", "target", "phase", "latency_seconds"]

    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If file is empty, write header
        if csvfile.tell() == 0:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "target": target,
            "phase": phase,
            "latency_seconds": latency_seconds
        })




def get_process_memory_mb():
    """
    Returns current process RSS memory in MB.
    """
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024**2  # MB

def log_memory(tag=""):
    rss_mb = get_process_memory_mb()
    print(f"[MEM] {tag} | RSS: {rss_mb:.2f} MB", flush=True)
    return rss_mb

def append_memory_to_csv(evaluation_path, target, epoch, phase, rss_mb,
                         tf_current_mb=None, tf_peak_mb=None):
    """
    Append memory usage info to a CSV file in EVALUATION_PATH.

    - target: "cpu" or "mem"
    - epoch: integer epoch number
    - phase: string, e.g. "before_fit", "after_fit", "incremental_epoch_start"
    - rss_mb: process RSS in MB
    - tf_current_mb / tf_peak_mb: optional, can be None if not using TF memory info
    """
    file_path = os.path.join(evaluation_path, f"memory_{target}.csv")

    fieldnames = ["epoch", "phase", "rss_mb", "tf_current_mb", "tf_peak_mb"]

    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If file is new, write header
        if csvfile.tell() == 0:
            writer.writeheader()

        writer.writerow({
            "epoch": epoch,
            "phase": phase,
            "rss_mb": rss_mb,
            "tf_current_mb": tf_current_mb if tf_current_mb is not None else "",
            "tf_peak_mb": tf_peak_mb if tf_peak_mb is not None else "",
        })

def get_tf_cpu_memory_mb():
    """
    Returns (current_mb, peak_mb) from TensorFlow CPU memory info, if available.
    """
    try:
        info = tf.config.experimental.get_memory_info('CPU:0')
        current_mb = info['current'] / 1024**2
        peak_mb = info['peak'] / 1024**2
        return current_mb, peak_mb
    except Exception:
        return None, None


# ----------------------------------------------------------------------
# (optional) Function to retrieve InternalIP from node name
# NOTE: no longer used for Prometheus; kept in case you need node IP elsewhere.
# ----------------------------------------------------------------------
def get_node_ip_from_name(node_name):
    config.load_incluster_config()  # Load cluster config
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    for address in node.status.addresses:
        if address.type == "InternalIP":
            return address.address
    return None


# ----------------------------------------------------------------------
# Prometheus metric querying helpers (instance-based)
# ----------------------------------------------------------------------
def query_metric(prometheus_url, promql_query):
    """Run an instant query against Prometheus and return the 'result' list."""
    encoded_query = urllib.parse.quote(promql_query)
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


def get_instance_for_node(node_name, prometheus_url=PROMETHEUS_URL):
    """
    Given a Kubernetes node name (e.g. 'kind-worker'),
    return the Prometheus 'instance' label for node_exporter.
    """
    query = f'node_uname_info{{nodename="{node_name}"}}'
    results = query_metric(prometheus_url, query)

    if not results:
        print(f"No node_uname_info found for nodename={node_name}", flush=True)
        all_results = query_metric(prometheus_url, "node_uname_info")
        print("Available node_uname_info metrics:", flush=True)
        for r in all_results:
            print("  metric:", r.get("metric", {}), flush=True)
        return None

    instance = results[0]["metric"].get("instance")
    #print(f"Resolved node '{node_name}' to instance '{instance}'", flush=True)
    return instance


def get_memory_usage(instance):
    """
    Memory usage in % for a given Prometheus instance label.
    """
    query = (
        f'100 * (node_memory_MemTotal_bytes{{instance="{instance}"}} '
        f'- node_memory_MemAvailable_bytes{{instance="{instance}"}}) '
        f'/ node_memory_MemTotal_bytes{{instance="{instance}"}}'
    )
    results = query_metric(PROMETHEUS_URL, query)
    if results:
        return float(results[0]['value'][1])
    else:
        print(f"No result found for instance {instance} (memory)", flush=True)
        return 0.0


def get_network_receive_rate(instance):
    """
    Network receive rate in BYTES/sec on eth0 for this instance.
    """
    query = (
        f'rate(node_network_receive_bytes_total{{instance="{instance}",'
        f'device="eth0"}}[1m])'
    )
    results = query_metric(PROMETHEUS_URL, query)
    if results:
        return float(results["0"]["value"][1]) if isinstance(results, dict) else float(results[0]["value"][1])
    return 0.0


def get_network_transmit_rate(instance):
    """
    Network transmit rate in BYTES/sec on eth0 for this instance.
    """
    query = (
        f'rate(node_network_transmit_bytes_total{{instance="{instance}",'
        f'device="eth0"}}[1m])'
    )
    results = query_metric(PROMETHEUS_URL, query)
    if results:
        return float(results[0]["value"][1])
    return 0.0


def get_node_load_average(instance):
    """
    1-minute load average for this instance.
    """
    query = f'node_load1{{instance="{instance}"}}'
    results = query_metric(PROMETHEUS_URL, query)
    if results:
        return float(results[0]["value"][1])
    return 0.0


def gather_metrics_for_30_seconds(node_name, prometheus_url=PROMETHEUS_URL):
    """
    Collect a snapshot of CPU, memory, network RX/TX and load1
    for the given node name, using Prometheus instance label.

    NOTE: despite the name, this currently returns a *single* timestamp
    and first value per metric, as expected by data_formulation().
    """
    instance = get_instance_for_node(node_name, prometheus_url)
    if not instance:
        print(f"Could not resolve instance for node: {node_name}", flush=True)
        return

    # CPU: total cores used (all modes except idle) for this instance
    cpu_query = (
        f'sum(irate(node_cpu_seconds_total{{mode!="idle",'
        f'instance="{instance}"}}[1m]))'
    )

    rows = []

    cpu_results = query_metric(prometheus_url, cpu_query)
    cpu_value = float(cpu_results[0]["value"][1]) if cpu_results else 0.0
    memory_value = get_memory_usage(instance)
    netw_receive_value = get_network_receive_rate(instance)
    netw_transmit_value = get_network_transmit_rate(instance)
    load_value = get_node_load_average(instance)

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Single row; data_formulation() will use the first element of each list
    rows.append({
        "timestamp": current_time,
        "cpu": cpu_value,
        "mem": memory_value,
        "network_receive": netw_receive_value,
        "network_transmit": netw_transmit_value,
        "load": load_value
    })

    data = {
        "timestamp": [row["timestamp"] for row in rows],
        "cpu": [row["cpu"] for row in rows],
        "mem": [row["mem"] for row in rows],
        "network_receive": [row["network_receive"] for row in rows],
        "network_transmit": [row["network_transmit"] for row in rows],
        "load": [row["load"] for row in rows],
    }
    return data


def data_formulation(data_flushed: list, path_to_data_file):
    transformed_data_list = [
        {
            key: value[0] if isinstance(value, list) and len(value) > 0 else None
            for key, value in dic.items()
        }
        for dic in data_flushed
    ]

    file_exists = os.path.isfile(path_to_data_file)

    with open(path_to_data_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=header)

        if not file_exists:
            writer.writeheader()

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
    print()
    print(f"[INFO]: Initial Training model for {target_resource}")
    logging.info(f"Start  the pre-training phase for target {target_resource}")
    training_df = init_training_.df_reformulation(target_metric=target_resource)
    train_x, train_y, validation_x, validation_y = init_training_.train_test_split_(training_df, sequence_length=sequence_length)
    logging.info(f"Start preprocessing training for target {target_resource}")
    model = init_training_.build_model()
    train_model(target_resource, model,train_x,train_y,validation_x, validation_y, num_epochs,early_stopping )
    path_to_model_file = SAVED_MODELS_PATH+"/"+f"model_{target_resource}.keras"
    model.save(path_to_model_file)
    print()
    print("saved")



def train_model(target_resource, simple_model, train_x, train_y,
                validation_x, validation_y, num_epochs, early_stopping):
    mse_list_init, rmse_list_init = [], []

    for epoch in range(num_epochs):
        epoch_num = epoch + 1
        logging.info(f"Model started training, is on {epoch_num} epoch")

        # 💾 Memory before fit
        rss_before = get_process_memory_mb()
        tf_curr_before, tf_peak_before = get_tf_cpu_memory_mb()
        append_memory_to_csv(EVALUATION_PATH, target_resource, epoch_num,
                             phase="before_fit", rss_mb=rss_before,
                             tf_current_mb=tf_curr_before, tf_peak_mb=tf_peak_before)

        simple_model.fit(train_x, train_y, epochs=epoch_num, verbose=1)

        # 💾 Memory after fit
        rss_after = get_process_memory_mb()
        tf_curr_after, tf_peak_after = get_tf_cpu_memory_mb()
        append_memory_to_csv(EVALUATION_PATH, target_resource, epoch_num,
                             phase="after_fit", rss_mb=rss_after,
                             tf_current_mb=tf_curr_after, tf_peak_mb=tf_peak_after)

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
def federated_learning_send(target_resource):
    file_to_be_sent = f"{FEDERATED_WEIGHTS_PATH_SEND_CLIENT}/{target_resource}_weights_{NODE_NAME}.json"

    # Ensure the folder exists
    os.makedirs(FEDERATED_WEIGHTS_PATH_SEND_CLIENT, exist_ok=True)

    # If file does not exist, create an empty weights file
    if not os.path.exists(file_to_be_sent):
        print(f"[WARN] File {file_to_be_sent} does not exist. Creating empty JSON...", flush=True)
        with open(file_to_be_sent, 'w') as f:
            json.dump({}, f, indent=4)

    # Load the weights
    with open(file_to_be_sent, 'r') as f:
        weights_data = json.load(f)



    # Validate structure: must be Dict[str, List[float]]
    if not weights_data or not all(isinstance(v, list) for v in weights_data.values()):
        print(f"[WARN] Weights file {file_to_be_sent} is empty or invalid — sending will be skipped.")
        return

    # Prepare and send the payload
    payload = {
        "client_id": NODE_NAME,
        "target_resource": target_resource,
        "client_model": weights_data
    }

    # Optional: print payload for debugging
    print("[DEBUG] Payload being sent: weights from the incremental trained model")
    #print(json.dumps(payload, indent=2), flush=True)

    print(f"[INFO] Sending weights for '{target_resource}' to FedAsync server from client '{NODE_NAME}'", flush=True)
    retries = 0
    max_retries = 5

    while retries < max_retries:
        try:
            response = requests.post(FEDERATION_URL_SEND, json=payload)
            if response.status_code == 200:
                print("[SUCCESS] FedAsync update applied:", response.json(), flush=True)
                break
            else:
                print(f"[ERROR] Server responded with status {response.status_code}, retrying...", flush=True)
        except Exception as e:
            print(f"[ERROR] Exception occurred: {e}", flush=True)

        retries += 1


    if retries == max_retries:
        print("[ERROR] Failed to send weights after multiple retries.", flush=True)



def federated_receive(target_resource, max_retries=5, retry_delay=2):
    url = f"{FEDERATION_URL_RECEIVE}/{target_resource}"
    retries = 0

    while retries < max_retries:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                model_data = data.get("model", {})

                if model_data:
                    print(f"🟢 [INFO] Aggregated weights for '{target_resource}' received (server_round: {data['server_round']})", flush=True)
                    print("🟢 [INFO] Aggregated weights have been updated!")
                    return model_data
                else:
                    print(f"[INFO] Model for '{target_resource}' is empty. Waiting...", flush=True)
            else:
                print(f"[WARN] Server responded with status {response.status_code}. Retrying...", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to fetch model: {e}", flush=True)

        retries += 1
        time.sleep(retry_delay)

    print("[ERROR] Max retries reached. No model received.")
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
    print(f"[DEBUG] NEW calculate_convergence called for target={target}", flush=True)
    mse_list, rmse_list, r2_list = [], [], []

    for file_ in os.listdir(path_):
        # ΜΟΝΟ αρχεία που ξεκινάνε με metrics_ (π.χ. metrics_cpu.csv)
        if not file_.startswith("metrics_"):
            continue
        if not file_.endswith(f"{target}.csv"):
            continue
 
        full_path = os.path.join(path_, file_)
        with open(full_path, "r") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                # Περιμένουμε στήλες MSE, RMSE, R2
                if "MSE" in row and row["MSE"]:
                    try:
                        mse_list.append(float(row["MSE"]))
                    except ValueError:
                        pass
                if "RMSE" in row and row["RMSE"]:
                    try:
                        rmse_list.append(float(row["RMSE"]))
                    except ValueError:
                        pass
                if "R2" in row and row["R2"]:
                    try:
                        r2_list.append(float(row["R2"]))
                    except ValueError:
                        pass


    if not mse_list or not rmse_list or not r2_list:
        return 0, 0, 0

    trend_mse  = trend_of_values(mse_list)
    trend_rmse = trend_of_values(rmse_list)
    trend_r2   = trend_of_values(r2_list)
    return trend_mse, trend_rmse, trend_r2



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

def preprocessing(data_flush_list, path_to_data_file, iterator):
    print(data_flush_list, flush=True)
    data_formulation(data_flush_list, path_to_data_file)
    row_count = count_csv_rows(path_to_data_file)

    if row_count >= 15:
        df = pd.DataFrame(csv_to_dict(path_to_data_file))

        # 🛠️ Preprocess and extract features regardless of iterator
        updated_df, causality_cpu, causality_ram = preprocess_time_series_data(df)
        features_cpu, features_ram = find_resource_features(causality_cpu, causality_ram, updated_df)

        # If you really want hard-coded features, keep these. Otherwise remove.
        features_cpu = ['mem', "network_receive", "network_transmit", "load"]
        features_ram = ['cpu', "network_receive", "network_transmit", "load"]

        if iterator == 0:
            # === INITIAL TRAINING ONLY ONCE ===
            init_training_ = DeepNeuralNetwork_Controller(df, features_cpu, features_ram)

            for target_resource in targets:
                init_training_based_on_resource(init_training_, target_resource, early_stopping)
                print("Initial training completed", flush=True)

            iterator += 1
            print(f"[DEBUG] Initial training done. Moving to iterator = {iterator}", flush=True)

            # ✅ Important: do NOT touch mse/rmse/r2 here; we don't have them yet
            clear_csv_content(path_to_data_file)
            print(f"[INFO]: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} Batch pre-processing completed", flush=True)
            print(df, flush=True)

            return iterator  # <-- early exit avoids UnboundLocalError

        # ============================================================
        # From here on: INCREMENTAL + FEDERATED logic (iterator != 0)
        # ============================================================
        print("🌀 Incremental procedure started", flush=True)
        incremental_training_ = DeepNeuralNetwork_Controller(updated_df, features_cpu, features_ram)

        for i in range(0, 3):
            for target_resource in targets:
                # Use the updated iterator coming back from incremental_training
                iterator, target_resource, predictions_ = incremental_training(
                    incremental_training_, target_resource, iterator
                )

                # ⛔ If incremental_training skipped (not enough samples), predictions_ is None
                if predictions_ is None:
                    print(f"[INFO] No predictions for {target_resource} this round "
                        f"(not enough samples). Skipping analysis and FL.", flush=True)
                    continue  # go to next target_resource

                if i % 2 == 0:
                    print(f"🧠 Predictions for {target_resource}", flush=True)
                    predictions_final_ = predictions_.tolist()

                    MAX_HISTORY = 20
                    for element in predictions_final_:
                        trained_model_predictions.append(element[0])
                        if len(trained_model_predictions) > MAX_HISTORY:
                            trained_model_predictions.pop(0)

                    result = analyze_rate_of_change(calculate_rate_of_change(trained_model_predictions))
                    print(f"[INFO] Rate of change analysis result: {result}", flush=True)

                    if result in (0, 1):
                        print("[INFO] No re-adaptation triggered. Normal trend or stable.", flush=True)
                    else:
                        print("⚠️ [TRIGGER] Re-adaptation condition met!", flush=True)
                        time.sleep(10)

                    predictions_final_ = []
                    print("[INFO] Post-prediction pause done. Continuing...", flush=True)
                    time.sleep(2)



                metrics_convergence = calculate_convergence(EVALUATION_PATH, target_resource)
                most_frequent_value = count_frequency(metrics_convergence)

                if len(most_frequent_value) == 1 and most_frequent_value[0] != 1:
                    print()
                    print("🚀 Welcome to Federated Learning!!", flush=True)
                    federated_learning_send(target_resource)
                    print("⏳ Waiting for global model aggregation...", flush=True)
                    time.sleep(5)

                    while True:
                        federated_weights = federated_receive(target_resource)
                        if federated_weights:
                            print()
                            print(f"[✅ INFO] Aggregated weights received for {target_resource}", flush=True)
                            time.sleep(2)
                            break
                        else:
                            print()
                            print(f"[INFO] Awaiting weights for {target_resource}...", flush=True)
                            time.sleep(2)

                    write_json_body(
                        f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_aggregated.json",
                        federated_weights
                    )

                else:
                    print()
                    print("📡 Triggering federated communication (fallback path)", flush=True)
                    time.sleep(1)
                    federated_learning_send(target_resource)
                    print()
                    print("⏳ Waiting for aggregation response...", flush=True)
                    time.sleep(5)

                    while True:
                        federated_weights = federated_receive(target_resource)
                        if federated_weights:
                            print(f"[✅ INFO] Aggregated weights received (fallback) for {target_resource}", flush=True)
                            time.sleep(2)
                            break
                        else:
                            print(f"[INFO] Still waiting for aggregated weights...", flush=True)
                            time.sleep(2)

                    write_json_body(
                        f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_{NODE_NAME}_aggregated.json",
                        federated_weights
                    )

                print(f"[INFO] ✅ Evaluating Federated Model for {target_resource}", flush=True)
                validation_df = incremental_training_.df_reformulation(target_resource)
                _, _, validation_x, validation_y = incremental_training_.train_test_split_(validation_df, sequence_length)

                fed_model = load_keras_model(
                    SAVED_MODELS_PATH + "/" + f"model_{target_resource}.keras",
                    custom_objects={'Attention': Attention}
                )
                fed_model = update_model_with_federated_weights(fed_model, target_resource)
                preds = fed_model.predict(validation_x)

                mse = calculate_mse(preds, validation_y)
                rmse = calculate_rmse(mse)
                r2 = calculate_r2_score(validation_y, preds)

                # ✅ Write metrics *here*, where they exist
                append_to_csv(EVALUATION_PATH, f"{target_resource}_FDL", mse, rmse, r2)

                metrics_dict = {"MSE": mse, "RMSE": rmse, "R2": r2}
                save_final_metrics_json(metrics_dict, target_resource)

                print(f"[INFO] ✅ Federated model evaluation completed for {target_resource}", flush=True)

            time.sleep(3)

        # shared cleanup after incremental processing
        clear_csv_content(path_to_data_file)
        print(f"[INFO]: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} Batch pre-processing completed", flush=True)
        print(df, flush=True)

    else:
        print(f"[INFO]: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} More data needed for preprocessing", flush=True)

    return iterator  # <-- still returned for both branches




def save_final_metrics_json(metrics_dict, target_resource):
    output_path = f"./exposed_metrics/final_metrics_{target_resource}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as json_file:
        json.dump(metrics_dict, json_file, indent=4)

    print(f"[📝] Final metrics saved to {output_path}", flush=True)


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
    print()
    print("============ INCREMENTAL PROCEDURE =======================", flush=True)

    # Safety / control parameters
    BATCH_SIZE = 32
    MAX_STEPS_PER_EPOCH = 5        # at most 5 batches per epoch
    MAX_FISHER_BATCHES = 3         # at most 3 batches for Fisher
    MIN_SAMPLES_FOR_TRAIN = 32     # now used only for WARN, not to skip

    # ⏱️ start timing the whole incremental step
    total_start_time = time.time()

    # --------------------------------------------------------
    # 1) Build dataset for this incremental step
    # --------------------------------------------------------
    old_model_file = os.path.join(SAVED_MODELS_PATH, f"model_{target_resource}.keras")
    training_incremental_df = incremental_training_.df_reformulation(target_resource)
    train_x, train_y, validation_x, validation_y = incremental_training_.train_test_split_(
        training_incremental_df, sequence_length
    )

    n_samples = len(train_x)
    print(f"[DEBUG] target={target_resource}, n_samples before cap = {n_samples}", flush=True)

    # ✅ only skip if we literally have 0 samples
    if n_samples == 0:
        print(f"[INFO] No samples at all for {target_resource}, skipping this round.", flush=True)
        return iterator, target_resource, None

    # ✅ if < MIN_SAMPLES_FOR_TRAIN, we still continue, just warn
    if n_samples < MIN_SAMPLES_FOR_TRAIN:
        print(f"[WARN] Only {n_samples} samples for {target_resource} "
              f"(less than {MIN_SAMPLES_FOR_TRAIN}). Training anyway with small batch.", flush=True)

    # Cap how many samples we use this round (prevents huge training times)
    max_train_samples = BATCH_SIZE * MAX_STEPS_PER_EPOCH   # e.g. 32 * 5 = 160
    if n_samples > max_train_samples:
        print(f"[INFO] Too many samples ({n_samples}). Using only {max_train_samples} for this round.", flush=True)
        idx = np.random.choice(n_samples, max_train_samples, replace=False)
        train_x = train_x[idx]
        train_y = train_y[idx]
        n_samples = max_train_samples

    # Load the old model and apply weights
    incremental_model = load_keras_model(old_model_file, custom_objects={'Attention': Attention})
    weights_file = os.path.join(WEIGHTS_PATH, f"{target_resource}_weights_{NODE_NAME}.weights.h5")
    incremental_model.save_weights(weights_file)
    print("weights saved", flush=True)
    print("⏳ Waiting briefly before next step...", flush=True)
    logging.info(f"model: {incremental_model} loaded")

    # Apply federated weights if they exist
    if len(os.listdir(FEDERATED_WEIGHTS_PATH_RECEIVE)) != 0 and len(os.listdir(FEDERATED_WEIGHTS_PATH_RECEIVE)) == 1:
        if file_contains_word(FEDERATED_WEIGHTS_PATH_RECEIVE, target_resource):
            incremental_model = update_model_with_federated_weights(incremental_model, target_resource)

    # ✅ keep partial batches (do NOT drop them)
    dataset_current_task = tf.data.Dataset.from_tensor_slices(
        (train_x, train_y)
    ).batch(BATCH_SIZE, drop_remainder=False)

    # Optimizer for training
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.01)

    # Store the initial parameters (θ*)
    prev_params = get_params(incremental_model)

    # ✅ ensure at least 1 step per epoch
    raw_steps = max(1, int(np.ceil(n_samples / BATCH_SIZE)))
    steps_per_epoch = min(raw_steps, MAX_STEPS_PER_EPOCH)
    print(f"[DEBUG] target={target_resource}, len(train_x)={n_samples}, "
          f"raw_steps={raw_steps}, steps_per_epoch={steps_per_epoch}", flush=True)

    # --------------------------------------------------------
    # 2) EWC: compute Fisher ONCE on a small subset
    # --------------------------------------------------------
    print("[EWC] Computing Fisher information on a subset...", flush=True)
    dataset_for_fisher = dataset_current_task.take(MAX_FISHER_BATCHES)
    t_fish_start = time.time()
    fisher = compute_fisher(incremental_model, dataset_for_fisher)
    t_fish_end = time.time()
    print(f"[EWC] Fisher computation finished in {t_fish_end - t_fish_start:.2f} seconds.", flush=True)

    # --------------------------------------------------------
    # 3) Main training loop (epochs × capped steps)
    # --------------------------------------------------------
    for epoch in range(epochs):
        epoch_num = epoch + 1
        batch_count = 0

        rss_start = get_process_memory_mb()
        tf_curr_start, tf_peak_start = get_tf_cpu_memory_mb()
        append_memory_to_csv(EVALUATION_PATH, target_resource, epoch_num,
                             phase="incremental_epoch_start", rss_mb=rss_start,
                             tf_current_mb=tf_curr_start, tf_peak_mb=tf_peak_start)

        try:
            for data, target in dataset_current_task:
                # Ensure data has a batch dimension if it's missing
                if len(data.shape) == 2:  # if shape is (2, 12), expand to (1, 2, 12)
                    data = tf.expand_dims(data, axis=0)

                # Gradient calculation
                with tf.GradientTape() as tape:
                    output = incremental_model(data)
                    loss = tf.keras.losses.mean_squared_error(target, output)

                    # EWC penalty reuses the SAME fisher each batch
                    ewc_loss = loss + ewc_penalty(
                        get_params(incremental_model),
                        prev_params,
                        fisher,
                        fisher_multiplier
                    )

                grads = tape.gradient(ewc_loss, incremental_model.trainable_variables)
                optimizer.apply_gradients(zip(grads, incremental_model.trainable_variables))

                batch_count += 1
                if batch_count >= steps_per_epoch:
                    break  # Stop after processing the expected number of batches

        except tf.errors.OutOfRangeError:
            print(f"End of dataset reached for epoch {epoch + 1}")

        rss_end = get_process_memory_mb()
        tf_curr_end, tf_peak_end = get_tf_cpu_memory_mb()
        append_memory_to_csv(EVALUATION_PATH, target_resource, epoch_num,
                             phase="incremental_epoch_end", rss_mb=rss_end,
                             tf_current_mb=tf_curr_end, tf_peak_mb=tf_peak_end)

        # Update params after each epoch
        prev_params = update_params(incremental_model, prev_params)

    # --------------------------------------------------------
    # 4) End-to-end time for incremental training step
    # --------------------------------------------------------
    total_duration = time.time() - total_start_time
    append_total_incremental_time_to_csv(
        EVALUATION_PATH,
        target_resource,
        phase="incremental_training_total",
        duration_seconds=total_duration
    )

    # --------------------------------------------------------
    # 5) Save model, run inference, log metrics
    # --------------------------------------------------------
    incremental_model.save_weights(os.path.join(
        WEIGHTS_PATH, f"{target_resource}_weights_{NODE_NAME}.weights.h5"
    ))
    incremental_model.save(os.path.join(
        SAVED_MODELS_PATH, f"model__{target_resource}.keras"
    ))
    weights_list = [arr.tolist() for arr in incremental_model.get_weights()]

    json_filepath = os.path.join(
        FEDERATED_WEIGHTS_PATH_SEND_CLIENT, f"{target_resource}_weights_{NODE_NAME}.json"
    )
    save_weights_to_json(weights_list, json_filepath)

    logging.info(f"fine-tuned model: fine_tuned_model model_{target_resource}.keras saved")
    logging.info(f"and the weights: fine_tuned_model_weights_{target_resource}.h5 saved")
    logging.info(f"and the weights: fine_tuned_model_weights_{target_resource}.json saved")

    # Perform validation and predictions (still measuring inference latency)
    validation_data = (validation_x, validation_y)

    t0 = time.time()
    predictions = incremental_model.predict(validation_data[0])
    inference_latency = time.time() - t0

    append_latency_to_csv(
        EVALUATION_PATH,
        target_resource,
        phase="incremental_inference",
        latency_seconds=inference_latency
    )

    mse = calculate_mse(predictions, validation_data[1])
    rmse = calculate_rmse(mse)
    r2_score = calculate_r2_score(validation_data[1], predictions)

    append_to_csv(EVALUATION_PATH, target_resource, mse, rmse, r2_score)
    print("metrics exposed, incremental model and fine-tuned weights saved")

    return iterator, target_resource, predictions



def append_total_incremental_time_to_csv(evaluation_path, target, phase, duration_seconds):
    """
    Append total incremental training time (all epochs together) to a CSV file.

    - evaluation_path: base folder (EVALUATION_PATH)
    - target: e.g. "cpu", "mem"
    - phase: e.g. "incremental_training_total"
    - duration_seconds: float, total elapsed time in seconds
    """
    file_path = os.path.join(evaluation_path, f"incremental_training_time_{target}.csv")
    fieldnames = ["timestamp", "target", "phase", "duration_seconds"]

    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If file is empty, write the header
        if csvfile.tell() == 0:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "target": target,
            "phase": phase,
            "duration_seconds": duration_seconds
        })


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

def save_weights_to_json(weights_list: list, json_file_path: str):
    """
    Save the weights of a Keras model to a JSON file with named keys,
    ensuring each weight is a flat list of floats as required by the server.
    """
    weights_dict = {}
    for i, weight in enumerate(weights_list):
        weights_dict[f"w_{i}"] = np.array(weight).flatten().tolist()

    with open(json_file_path, 'w') as f:
        json.dump(weights_dict, f, indent=4)

    print(f"[INFO] Saved weights to {json_file_path}")






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

import json

def update_model_with_federated_weights(loaded_model, target_resource):
    possible_files = [
        f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_aggregated.json",
        f"{FEDERATED_WEIGHTS_PATH_RECEIVE}/{target_resource}_weights_{NODE_NAME}_aggregated.json"
    ]

    for file_path in possible_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as json_file:
                    raw_data = json_file.read().strip()

                    if not raw_data:
                        raise ValueError(f"[❌ ERROR] File '{file_path}' is empty")

                    weights_data = json.loads(raw_data)

                print(f"[✅ INFO] Loaded federated weights from {file_path}", flush=True)

                # Apply weights to the model
                for layer in loaded_model.layers:
                    if layer.name in weights_data:
                        layer.set_weights([
                            np.array(weights_data[layer.name][param])
                            for param in layer.trainable_weights
                        ])

                delete_file(file_path)
                return loaded_model

            except (json.JSONDecodeError, ValueError) as e:
                print(f"[❌ ERROR] Failed to load weights from {file_path}: {e}", flush=True)
                print("[⚠️ DEBUG] Content was:", flush=True)
                with open(file_path, 'r') as f:
                    print(f.read(), flush=True)
                return loaded_model  # Return original model if failed

    print(f"[❌ ERROR] No valid federated weights file found for '{target_resource}'", flush=True)
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
    print()
    print("📥 Data inserted, pre-processing process is initialized", flush=True)
    print()  # This adds a newline
    print("🔍 Missing values detection and imputation", flush=True)
    print()  # This adds a newline
    pipeline.missing_values()
    print("🛠️ Feature engineering", flush=True)
    print()  # This adds a newline
    pipeline.feature_engineering("cpu")
    pipeline.feature_engineering("mem")
    print("📏 Normalization", flush=True)
    pipeline.normalization()
    causality_cpu = pipeline.get_causality(column_name="cpu")
    causality_ram  = pipeline.get_causality(column_name="mem")
    #dict_data= pipeline.df.to_dict(orient='list')
    pipeline.erase_rate_of_change_metrics()

    # Print the JSON data
    return pipeline.df,causality_cpu, causality_ram



    