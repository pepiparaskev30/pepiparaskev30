import requests
import json, time
import pandas as pd
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()


PROMETHEUS_URL = "http://localhost:9098"
NODE_INSTANCE = "192.168.67.2:9100"

import requests

def get_cpu_usage(instance, prometheus_url = PROMETHEUS_URL):
    """
    Fetches CPU usage breakdown for a given node instance from Prometheus.

    Args:
        instance (str): e.g. "192.168.67.2:9100"
        prometheus_url (str): e.g. "http://localhost:9098"

    Returns:
        dict: {
            "total": float,
            "used": float,
            "usage_percent": float,
            "raw_used": float,
            "modes": dict (mode -> value)
        }
    """
    query = f'sum by (mode) (irate(node_cpu_seconds_total{{instance="{instance}"}}[5m]))'
    response = requests.get(f"{prometheus_url}/api/v1/query", params={"query": query})

    if response.status_code != 200:
        raise RuntimeError(f"Error querying Prometheus: {response.status_code}")

    results = response.json().get("data", {}).get("result", [])
    if not results:
        raise RuntimeError("No CPU data returned for instance.")

    cpu_modes = {}
    total = 0.0

    for item in results:
        mode = item["metric"]["mode"]
        value = float(item["value"][1])
        cpu_modes[mode] = value
        total += value

    idle = cpu_modes.get("idle", 0.0)
    used = total - idle
    usage_percent = (used / total) * 100 if total > 0 else 0.0
    raw_used = used / total if total > 0 else 0.0

    return {
        "cpu_usage": raw_used
    }


def get_memory_metric(metric_name, instance):
    query = f'{metric_name}{{instance="{instance}"}}'
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
    if response.status_code != 200:
        raise RuntimeError(f"Failed to query {metric_name}")
    results = response.json().get("data", {}).get("result", [])
    if not results:
        raise RuntimeError(f"No data for {metric_name}")
    return float(results[0]["value"][1])

def get_memory_usage(instance):
    try:
        total_bytes = get_memory_metric("node_memory_MemTotal_bytes", instance)
        avail_bytes = get_memory_metric("node_memory_MemAvailable_bytes", instance)
    except RuntimeError as e:
        print(e)
        return

    used_bytes = total_bytes - avail_bytes
    usage_percent = (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0
    usage_raw = used_bytes / total_bytes

    # Convert to human-readable
    to_gb = lambda b: b / (1024 ** 3)

    # Output
    return {"ram_usage": usage_raw}

def get_network_receive_rate(instance, prometheus_url = PROMETHEUS_URL, device="eth0", max_bandwidth_bps=1_000_000_000):
    """
    Returns normalized network receive rate (0–1) for a given interface.

    Args:
        instance (str): Node IP and port, e.g., "192.168.67.2:9100"
        prometheus_url (str): Prometheus base URL
        device (str): Network interface, default "eth0"
        max_bandwidth_bps (int): Max interface capacity in bytes/sec (default 1 Gbps)

    Returns:
        dict: {
            "net_rx_bytes_per_sec": float,
            "net_rx_normalized": float
        }
    """
    query = f'rate(node_network_receive_bytes_total{{instance="{instance}",device="{device}"}}[1m])'
    response = requests.get(f"{prometheus_url}/api/v1/query", params={"query": query})
    
    if response.status_code != 200:
        raise RuntimeError(f"Prometheus query failed: {response.status_code}")
    
    result = response.json().get("data", {}).get("result", [])
    rate = float(result[0]["value"][1]) if result else 0.0

    normalized = rate / max_bandwidth_bps if max_bandwidth_bps > 0 else 0.0

    return {
        "net_rx_bytes_per_sec": rate,
        "net_rx_normalized": min(normalized, 1.0)  # Clamp to 1.0 if it spikes over max
    }


def get_network_transmit_rate(instance, prometheus_url = PROMETHEUS_URL, device="eth0", max_packets_per_sec=1_000_000):
    """
    Returns the normalized transmit packet rate (0–1) for a given interface.

    Args:
        instance (str): e.g., "192.168.67.2:9100"
        prometheus_url (str): Prometheus base URL
        device (str): Network interface, default "eth0"
        max_packets_per_sec (int): Expected maximum packet rate for normalization

    Returns:
        dict: {
            "net_tx_packets_per_sec": float,
            "net_tx_normalized": float
        }
    """
    query = f'rate(node_network_transmit_packets_total{{instance="{instance}",device="{device}"}}[1m])'
    response = requests.get(f"{prometheus_url}/api/v1/query", params={"query": query})

    if response.status_code != 200:
        raise RuntimeError(f"Prometheus query failed: {response.status_code}")
    
    result = response.json().get("data", {}).get("result", [])
    rate = float(result[0]["value"][1]) if result else 0.0

    normalized = rate / max_packets_per_sec if max_packets_per_sec > 0 else 0.0

    return {
        "net_tx_packets_per_sec": rate,
        "net_tx_normalized": min(normalized, 1.0)  # Clamp to 1.0 if exceeded
    }

def get_node_load_average(instance, prometheus_url=PROMETHEUS_URL, load_type="node_load1", core_count=8):
    """
    Fetches the normalized load average (1m, 5m, or 15m) for a given node.
    Normalized by core count.
    """
    if load_type not in {"node_load1", "node_load5", "node_load15"}:
        raise ValueError("Invalid load_type. Must be one of: 'node_load1', 'node_load5', 'node_load15'.")

    query = f'{load_type}{{instance="{instance}"}}'
    url = f'{prometheus_url}/api/v1/query'
    response = requests.get(url, params={'query': query})

    if response.status_code != 200:
        raise RuntimeError(f"Prometheus query failed: HTTP {response.status_code}")

    result = response.json().get("data", {}).get("result", [])
    load = float(result[0]["value"][1]) if result else 0.0

    # Normalize by core count (cap at 1.0)
    return min(load / core_count, 1.0)



num_samples = 30  # ~1 minute of data if every 2s
df = pd.DataFrame()

for _ in range(num_samples):
    try:
        # Capture current timestamp
        timestamp = datetime.utcnow().isoformat()

        # Collect metrics
        data = {
            "timestamp": timestamp,
            "cpu_usage": get_cpu_usage(NODE_INSTANCE),
            "memory_usage": get_memory_usage(NODE_INSTANCE),
            "net_rx_norm": get_network_receive_rate(NODE_INSTANCE),
            "net_tx_norm": get_network_transmit_rate(NODE_INSTANCE),
            "load_1m_norm": get_node_load_average(NODE_INSTANCE, load_type="node_load1", core_count=8),
        }

        # Append to DataFrame
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)

        print(data)  # Optional: print live sample
        time.sleep(2)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)

# Optional: Save to CSV
df.to_csv("node_monitoring_data.csv", index=False)