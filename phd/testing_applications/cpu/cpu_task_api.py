from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time, os
import random
import math
import requests
from kubernetes import client, config
import urllib.parse

app = FastAPI()


PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
NODE_NAME = os.getenv("NODE_NAME")

# List of workers and their points
list_with_workers = ["worker_1", "worker_2", "worker_3"]
points_of_workers = [(10, 30), (50, 50), (60, 70)]

# Define the distance threshold
threshold = 20  # You can adjust this value

# Pydantic model for request validation
class RequestData(BaseModel):
    num_users: int

# Function to query Prometheus metrics
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

def get_node_load_average(node_ip):
    query = f'node_load1{{instance="{node_ip}:9100"}}'
    url = f'{PROMETHEUS_URL}/api/v1/query'
    response = requests.get(url, params={'query': query})
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            load_average = float(data["data"]["result"][0]["value"][1])
            return load_average
        else:
            return 0
    else:
        print(f"Failed to fetch data from Prometheus. HTTP Status Code: {response.status_code}")
        return 0

# Function to retrieve the internal IP of a node by its name
def get_node_ip_from_name(node_name):
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    for address in node.status.addresses:
        if address.type == "InternalIP":
            return address.address
    return None

# Function to calculate Euclidean distance
def euclidean_distance(point1, point2):
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)

# Function to calculate the percentage of points close to A
def calculate_percentage_close(points, A, threshold):
    close_count = sum(1 for point in points if euclidean_distance(point, A) <= threshold)
    percentage = (close_count / len(points)) * 100
    return percentage

def get_proximity_per_worker(list_with_workers, points_of_workers, user_points):
    list_with_proximities_per_worker = []
    for worker, point in zip(list_with_workers, points_of_workers):
        list_with_proximities_per_worker.append((worker, calculate_percentage_close(user_points, point, threshold)))
    return list_with_proximities_per_worker

# Function to calculate latency for CPU-intensive tasks
def calculate_latency_cpu(num_users, proximity_percentage, current_load):
    max_capacity = 100
    cpu_factor = 1.5
    adjusted_load = min(current_load, max_capacity)
    latency = ((adjusted_load + num_users) / max_capacity) * (1 - proximity_percentage[0][1]) * cpu_factor
    latency_ms = latency * 1000
    return latency_ms

# API endpoint to handle POST requests for CPU-intensive tasks
@app.post("/api/cpu_latency")
async def cpu_latency(data: RequestData):
    print(data.num_users)
    if data.num_users < 10 or data.num_users > 50:
        raise HTTPException(status_code=400, detail="num_users must be an integer between 10 and 50")
    
    user_points = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(data.num_users)]
    proximity_percentage = get_proximity_per_worker(list_with_workers, points_of_workers, user_points)
    node_ip = get_node_ip_from_name(NODE_NAME)
    print(node_ip,flush=True)
    current_load = get_node_load_average(node_ip)
    print(current_load, flush=True)

    latency_ms = calculate_latency_cpu(data.num_users, proximity_percentage, current_load)
    
    #time.sleep(latency_ms / 1000)
    
    return {
        'message': f'Latency applied: {latency_ms} ms',
        'num_users': data.num_users,
        'proximity_percentage': proximity_percentage,
        'current_load': current_load
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
