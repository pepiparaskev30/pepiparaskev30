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
import time,os
import numpy as np
import csv
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
from sklearn.impute import SimpleImputer


############  START logging properties #################
#ignore information messages from terminal
warnings.filterwarnings("ignore")
############ END logging properties #################

#module classes that helps in the pre-processing
label_encoder = LabelEncoder()
scaler = StandardScaler()

# useful variables
global header
header = ["timestamp", "cpu", "mem", "network_receive", "network_transmit", "disk_read", "disk_write", "disk_usage", "load", "uptime"]

# useful ENV_VARIABLES

DATA_GENERATION_PATH = "./data_generation_path/data.csv"


class Gatherer:
    # Flag to check if the threads are ready to collect information
    ready_flag = True
    # Lists to store the results used by CA, RL and GNN
    prometheus_data_queue = Queue()

    # Amount of time to wait before starting a new thread
    wait_time = int(os.getenv('WAIT_TIME', '10'))

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
        print(data_list, flush=True)
        #preprocessing(data_list, DATA_GENERATION_PATH)
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
def query_metric(PROMETHEUS_URL, promql_query):
    encoded_query = urllib.parse.quote(promql_query)
    url = f"{PROMETHEUS_URL}/api/v1/query?query={encoded_query}"

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

def gather_metrics_for_30_seconds(node_name):
    # Resolve node IP from node name
    node_ip = get_node_ip_from_name(node_name)
    PROMETHEUS_URL = f'{node_ip}:30000'
    if not node_ip:
        print(f"Could not resolve IP for node: {node_name}")
        return

    # Adjust queries to filter by node's IP with a 1-second interval
    cpu_query = f'sum(irate(node_cpu_seconds_total{{mode="user",instance="{node_ip}:9100"}}[1m]))'

    memory_query = f'100 * (node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}} - node_memory_MemAvailable_bytes{{instance="{node_ip}:9100"}}) / node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}}'

    # Network Bandwidth Queries (with 1-second interval)
    network_receive_query = f'irate(node_network_receive_bytes_total{{instance="{node_ip}:9100", device!="lo"}}[1m])'
    network_transmit_query = f'irate(node_network_transmit_bytes_total{{instance="{node_ip}:9100", device!="lo"}}[1m])'

    # Disk I/O Queries (with 1-second interval)
    disk_read_query = f'irate(node_disk_read_bytes_total{{instance="{node_ip}:9100"}}[1m])'
    disk_write_query = f'irate(node_disk_write_bytes_total{{instance="{node_ip}:9100"}}[1m])'

    # Disk Usage Query (for ext4 file systems)
    disk_usage_query = f'100 * (node_filesystem_size_bytes{{instance="{node_ip}:9100",fstype="ext4"}} - node_filesystem_free_bytes{{instance="{node_ip}:9100",fstype="ext4"}}) / node_filesystem_size_bytes{{instance="{node_ip}:9100",fstype="ext4"}}'

    # Load Average Query
    load_query = f'node_load1{{instance="{node_ip}:9100"}}'

    # Uptime Query
    uptime_query = f'node_time_seconds{{instance="{node_ip}:9100"}}'


    rows = []

    # Querying all metrics with 1-second scrape intervals
    cpu_results = query_metric(PROMETHEUS_URL,cpu_query)
    memory_results = query_metric(PROMETHEUS_URL,memory_query)
    network_receive_results = query_metric(PROMETHEUS_URL,network_receive_query)
    network_transmit_results = query_metric(PROMETHEUS_URL,network_transmit_query)
    disk_read_results = query_metric(PROMETHEUS_URL,disk_read_query)
    disk_write_results = query_metric(PROMETHEUS_URL,disk_write_query)
    disk_usage_results = query_metric(PROMETHEUS_URL,disk_usage_query)
    load_results = query_metric(PROMETHEUS_URL,load_query)
    uptime_results = query_metric(PROMETHEUS_URL,uptime_query)

    # Collect current timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Extract CPU, Memory, Network, Disk, Load, and Uptime data
    for cpu_result in cpu_results:
        instance = cpu_result['metric'].get('instance', 'unknown')
        cpu_value = float(cpu_result['value'][1])  # The value is a [timestamp, value] pair

        memory_value = None
        for mem_result in memory_results:
            if mem_result['metric'].get('instance') == instance:
                memory_value = float(mem_result['value'][1])
                break

        network_receive_value = None
        for net_recv_result in network_receive_results:
            if net_recv_result['metric'].get('instance') == instance:
                network_receive_value = float(net_recv_result['value'][1])
                break

        network_transmit_value = None
        for net_transmit_result in network_transmit_results:
            if net_transmit_result['metric'].get('instance') == instance:
                network_transmit_value = float(net_transmit_result['value'][1])
                break

        disk_read_value = None
        for disk_read_result in disk_read_results:
            if disk_read_result['metric'].get('instance') == instance:
                disk_read_value = float(disk_read_result['value'][1])
                break

        disk_write_value = None
        for disk_write_result in disk_write_results:
            if disk_write_result['metric'].get('instance') == instance:
                disk_write_value = float(disk_write_result['value'][1])
                break

        disk_usage_value = None
        for disk_usage_result in disk_usage_results:
            if disk_usage_result['metric'].get('instance') == instance:
                disk_usage_value = float(disk_usage_result['value'][1])
                break

        load_value = None
        for load_result in load_results:
            if load_result['metric'].get('instance') == instance:
                load_value = float(load_result['value'][1])
                break

        uptime_value = None
        for uptime_result in uptime_results:
            if uptime_result['metric'].get('instance') == instance:
                uptime_value = float(uptime_result['value'][1])
                break

        # Add row with collected data
        rows.append({
            "timestamp": current_time,
            "cpu": cpu_value,
            "mem": memory_value,
            "network_receive": network_receive_value,
            "network_transmit": network_transmit_value,
            "disk_read": disk_read_value,
            "disk_write": disk_write_value if disk_write_value != "" else 0,
            "disk_usage": disk_usage_value,
            "load": load_value,
            "uptime": uptime_value
        })

    # Transform data into the specified format
    data = {
        "timestamp": [row["timestamp"] for row in rows],
        "cpu": [row["cpu"] for row in rows],
        "mem": [row["mem"] for row in rows],
        "network_receive": [row["network_receive"] for row in rows],
        "network_transmit": [row["network_transmit"] for row in rows],
        "disk_read": [row["disk_read"] for row in rows],
        "disk_write": [row["disk_write"] for row in rows],
        "disk_usage": [row["disk_usage"] for row in rows],
        "load": [row["load"] for row in rows],
        "uptime": [row["uptime"] for row in rows]
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
        "disk_read": [],
        "disk_write": [],
        "disk_usage": [],
        "load": [],
        "uptime": []
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
            
            # Check and convert the "disk_read" value
            data["disk_read"].append(float(row["disk_read"]) if row["disk_read"] else 0.0)
            
            # Check and convert the "disk_write" value
            data["disk_write"].append(float(row["disk_write"]) if row["disk_write"] else 0.0)
            
            # Check and convert the "disk_usage" value
            data["disk_usage"].append(float(row["disk_usage"]) if row["disk_usage"] else 0.0)
            
            # Check and convert the "load" value
            data["load"].append(float(row["load"]) if row["load"] else 0.0)
            
            # Check and convert the "uptime" value
            data["uptime"].append(float(row["uptime"]) if row["uptime"] else 0.0)


    return data   

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


def preprocessing(data_flush_list,path_to_data_file):
    data_formulation(data_flush_list,path_to_data_file)
    row_count = count_csv_rows(path_to_data_file)
    if row_count>=12:
        df = pd.DataFrame(csv_to_dict(path_to_data_file))
        updated_df, causality_cpu, causalilty_ram=preprocess_time_series_data(df)
        print(causalilty_ram, flush=True)
        print(causality_cpu, flush=True)
        print(updated_df, flush=True)
        clear_csv_content(path_to_data_file)
        print(f"[INFO]: {datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} Batch pre-processing started", flush=True)
        print(df, flush=True)
        
    else:
        print(f"[INFO]: {datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} more lines needed for data preprocessing", flush=True)



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
        self.adjust_columns()  # Assuming this method adjusts columns if needed
        
        """
        Find Causality Among Time Series Features

        This function performs granger causality analysis to investigate the relationships between a target feature and a set of time series features.
        """
        
        # Identify and remove constant columns (those with only one unique value)
        constant_columns = [col for col in self.df.columns if self.df[col].nunique() == 1]
        if constant_columns:
            print(f"Constant columns detected and removed: {constant_columns}")
            self.df = self.df.drop(columns=constant_columns)
        
        causality = []
        
        # Iterate through all the float columns to check causality with the specified column
        for column in self.float_columns:
            if column != column_name:
                # Perform Granger causality test for each column, suppressing output
                with StringIO() as buf, redirect_stdout(buf):
                    try:
                        # Perform Granger causality test
                        granger_causality = grangercausalitytests(self.df[[column_name, column]], maxlag=[1])

                        # Extract the p-value from the result (using 'ssr_ftest' to get the p-value for F-test)
                        p_value = list(granger_causality.values())[0][0]['ssr_ftest'][1]

                        # If p-value is less than 0.05, consider it a significant causality
                        if p_value < 0.05:
                            causality.append(column)
                    except Exception as e:
                        print(f"Error with Granger causality for {column}: {e}")
                        # Optionally handle errors (skip or add handling code here)
        
        # Return 0 if no causality is found, otherwise return the list of causally related columns
        if not causality:
            return 0
        else:
            return causality
    
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
    