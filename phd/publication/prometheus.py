import requests
import json

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
def get_network_receive_rate(instance, prometheus_url = PROMETHEUS_URL, device="eth0"):
    """
    Returns network receive rate (bytes/sec) for a specific interface on the node.
    """
    query = f'rate(node_network_receive_bytes_total{{instance="{instance}",device="{device}"}}[1m])'
    response = requests.get(f"{prometheus_url}/api/v1/query", params={"query": query})
    if response.status_code != 200:
        raise RuntimeError(f"Prometheus query failed: {response.status_code}")
    result = response.json().get("data", {}).get("result", [])
    return float(result[0]["value"][1]) if result else 0.0


print(get_cpu_usage(NODE_INSTANCE))
print(get_memory_usage(NODE_INSTANCE))
print(get_network_receive_rate(NODE_INSTANCE))