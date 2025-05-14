import os
import time
import json
from datetime import datetime
import urllib
import requests
import pandas as pd
from kubernetes import client, config

# Environment setup
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
NODE_NAME = os.getenv("NODE_NAME")
DATA_GENERATION_DIR = "./data_generation_path"
CSV_FILEPATH = os.path.join(DATA_GENERATION_DIR, "metrics_log.csv")

def get_node_ip_from_name(node_name):
    try:
        config.load_incluster_config()
        configuration = client.Configuration.get_default_copy()
        if os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true":
            configuration.verify_ssl = False
            print("[⚠️ WARN] SSL verification is disabled. Use only for development!")
        client.Configuration.set_default(configuration)

        v1 = client.CoreV1Api()
        node = v1.read_node(name=node_name)

        for address in node.status.addresses:
            if address.type == "InternalIP":
                return address.address

    except client.exceptions.ApiException as e:
        print(f"[ERROR] Kubernetes API exception while retrieving node IP: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error while getting node IP: {e}")
    return None


def query_metric(prometheus_url, promql_query):
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


def get_memory_usage(node_ip):
    query = f'100 * (node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}} - node_memory_MemAvailable_bytes{{instance="{node_ip}:9100"}}) / node_memory_MemTotal_bytes{{instance="{node_ip}:9100"}}'
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
    if response.status_code == 200:
        result = response.json().get('data', {}).get('result', [])
        if result:
            return float(result[0]['value'][1])
        else:
            print(f"No result found for memory usage on {node_ip}")
            return 0.0
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return 0.0


def get_network_receive_rate(node_ip):
    query = f'rate(node_network_receive_bytes_total{{instance="{node_ip}:9100",device="eth0"}}[1m])'
    response = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': query})
    if response.status_code == 200:
        result = response.json()
        if result["status"] == "success" and result["data"]["result"]:
            return float(result["data"]["result"][0]["value"][1])
        else:
            return 0.0
    else:
        print(f"Failed to query Prometheus: {response.status_code}", flush=True)
        return 0.0


def get_network_transmit_rate(node_ip):
    query = f'rate(node_network_transmit_packets_total{{instance="{node_ip}:9100",device="eth0"}}[1m])'
    response = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': query})
    if response.status_code == 200:
        result = response.json()
        if result["status"] == "success" and result["data"]["result"]:
            return float(result["data"]["result"][0]["value"][1])
        else:
            return 0.0
    else:
        print(f"Failed to query Prometheus: {response.status_code}", flush=True)
        return 0.0


def get_node_load_average(node_ip):
    query = f'node_load1{{instance="{node_ip}:9100"}}'
    response = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': query})
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            return float(data["data"]["result"][0]["value"][1])
        else:
            return 0.0
    else:
        print(f"Failed to fetch load average. HTTP {response.status_code}")
        return 0.0


def gather_metrics_for_30_seconds(node_name, prometheus_url=PROMETHEUS_URL):
    node_ip = get_node_ip_from_name(node_name)
    if not node_ip:
        raise RuntimeError(f"Could not resolve IP for node: {node_name}")

    cpu_query = f'sum(irate(node_cpu_seconds_total{{mode="user",instance="{node_ip}:9100"}}[1m]))'
    cpu_results = query_metric(prometheus_url, cpu_query)

    memory_value = get_memory_usage(node_ip)
    net_recv_value = get_network_receive_rate(node_ip)
    net_transmit_value = get_network_transmit_rate(node_ip)
    load_value = get_node_load_average(node_ip)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    rows = []
    for cpu_res in cpu_results:
        cpu_value = float(cpu_res['value'][1])
        rows.append({
            "timestamp": timestamp,
            "cpu": cpu_value,
            "mem": memory_value,
            "network_receive": net_recv_value,
            "network_transmit": net_transmit_value,
            "load": load_value
        })

    if not rows:
        rows.append({
            "timestamp": timestamp,
            "cpu": 0.0,
            "mem": memory_value,
            "network_receive": net_recv_value,
            "network_transmit": net_transmit_value,
            "load": load_value
        })

    return pd.DataFrame(rows)


def save_dataframe_to_csv(df: pd.DataFrame, file_path: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)
    df.to_csv(file_path, mode='a', header=not file_exists, index=False)


# Main loop
if __name__ == "__main__":
    while True:
        try:
            df_metrics = gather_metrics_for_30_seconds(NODE_NAME)
            save_dataframe_to_csv(df_metrics, CSV_FILEPATH)
            print(f"✅ Appended {len(df_metrics)} rows to {CSV_FILEPATH}")
        except Exception as e:
            print(f"❌ Failed to gather and save metrics: {e}")
        time.sleep(1)
