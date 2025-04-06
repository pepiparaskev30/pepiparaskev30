import random, os
from math import sqrt
import time
import math
import numpy as np
import requests

# Simulation constants
NUM_PODS = 2  # Number of service pods
ARRIVAL_INTERVAL_MEAN = 3  # Average arrival interval in seconds
SERVICE_TIME_MIN = 0.01  # Minimum service time in seconds
SERVICE_TIME_MAX = 0.025  # Maximum service time in seconds
NODE_NAME = os.getenv("NODE_NAME", "minikube")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", None)
NODE_COORDINATES = (10, 30)  # Node coordinates (fixed location)
LATENCY_PER_UNIT_DISTANCE = 0.0005  # Latency per unit distance in seconds
DATA_SIZE_MIN = 100  # Minimum data size in bytes
DATA_SIZE_MAX = 1000  # Maximum data size in bytes

def cpu_intensive_task(distance_to_node):
    duration = math.sqrt(distance_to_node)/10
    """Simulate a CPU-intensive task and return the time taken."""
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Perform a large number of mathematical operations
        for i in range(1000000):
            i * i
    
    end_time = time.time()
    time_taken = end_time - start_time
    
    print(f"CPU-intensive task completed in {time_taken:.2f} seconds")
    return time_taken

def ram_intensive_task(task_id, size_mb, distance_to_node):
    duration = math.sqrt(distance_to_node)/10
    """Simulates a RAM-intensive task by allocating large arrays."""
    print(f"Task {task_id}: Starting RAM-intensive task with {size_mb} MB allocation")
    try:
        # Allocate memory
        data = bytearray(size_mb * 1024 * 1024)
        # Simulate processing time
        time.sleep(duration)
    except MemoryError:
        print(f"Task {task_id}: Memory allocation failed")
    finally:
        print(f"Task {task_id}: Completed RAM-intensive task")

def network_intensive_task(camera_id_user, data_size_mb, frame_size_kb, distance_to_node):

    """
    Simulates AI-based analytics on the edge server.
    
    Parameters:
    - data_size_mb: Total data size in megabytes.
    - frame_size_kb: Size of each frame in kilobytes.
    """
    frame_size_kb = random.choice([30,50])
    duration  = math.sqrt(distance_to_node)/10
    # Calculate the number of frames based on data size and frame size
    num_frames = int((data_size_mb * 1024) / frame_size_kb)
    
    # Simulate latency based on distance to the node
    duration = math.sqrt(distance_to_node) / 10
    
    print(f"Camera {camera_id_user}: Starting edge processing for {num_frames} frames...")
    
    for frame in range(num_frames):
        # Simulate processing time per frame
        time.sleep(random.uniform(0.05, 0.2))  # Simulate processing latency
        if random.random() < 0.1:  # Simulate anomaly detection with 10% probability
            print(f"Camera {camera_id_user}: Anomaly detected in frame {frame + 1}")


# Global variables to track totals and metrics
total_latency = 0
total_distance = 0
num_users_served = 0
total_users_generated = 0

# Define the distance threshold (in units)
threshold = 30

# Function to calculate the percentage of points close to A
def calculate_percentage_close(points, A, threshold):
    close_count = sum(1 for point in points if calculate_distance(point, A) <= threshold)
    percentage = (close_count / len(points)) * 100
    return percentage


def get_proximity_per_worker(list_with_workers:list, points_of_workers:list, user_points):
    list_with_proximities_per_worker = []
    for worker, point in zip(list_with_workers, points_of_workers):
        list_with_proximities_per_worker.append((worker, calculate_percentage_close(user_points, point, threshold)))
    return list_with_proximities_per_worker

# Function to calculate Euclidean distance
def calculate_distance(coord1, coord2):
    """Calculate the Euclidean distance between two points."""
    return sqrt((coord2[0] - coord1[0]) ** 2 + (coord2[1] - coord1[1]) ** 2)

# Function to simulate user arrival and service
def simulation(name, user_coordinates, data_size, distance_to_node, replicas, migration_cost):
    global total_latency, total_distance
    #print(f"{name} arrives - coordinates {user_coordinates} and data size {data_size} bytes, and distance from the node {distance_to_node}")
    time.sleep(1)
    cpu_available_query = '100 * sum(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance) / sum(machine_cpu_cores) by (instance)'
    memory_available_query = '100 * (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)'
    total_memory_query = 'node_memory_MemTotal_bytes'
    try:
        cpu_available = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': cpu_available_query})
        memory_available = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': memory_available_query})
        memory_total = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params={'query': total_memory_query})

    except Exception as e:
        print("Not available Prometheus svc, random values are generated...")
        time.sleep(3)
        cpu_available = 80  # Percentage
        memory_available = 5  # GB
        memory_total = 16  # GB

    #print(f"{name} arrives - coordinates {user_coordinates} and data size {data_size} bytes, and distance from the node {distance_to_node}")

    # Simulate distance-based latency
    distance_latency = distance_to_node * LATENCY_PER_UNIT_DISTANCE
    # Simulate data size-based latency (e.g., larger data takes longer to process)
    data_latency = data_size * 0.000001  # Example: 1 byte adds 1 microsecond latency
    service_time = cpu_intensive_task(distance_to_node)
    # Calculate total latency (distance latency + data latency + service time)
    total_latency_for_user = distance_latency + data_latency + service_time
    total_latency += total_latency_for_user


    return {
        "user id": name, 
        "user coordinates": user_coordinates,
        "data input size": data_size, 
        "distance from node (in units)": distance_to_node, 
        "total latency": total_latency, 
        "utility": utility(cpu_available, memory_available, memory_total, total_latency, replicas,migration_cost)
    }

def utility(cpu_available, memory_available, memory_total, latency, replicas, migration_cost,replicas_optimal=2):
    alpha = 0.3
    beta = 0.1
    gamma = 0.3
    delta = 0.2
    epsilon = 0.1

    utility = alpha * (cpu_available / 100) + beta * (memory_available / memory_total) + gamma * (1 / latency) + delta * (replicas / replicas_optimal) - epsilon * (1/migration_cost)
    
    return utility


def generate_gaussian_int_samples(mean=50, std=30, num_samples=100):
    """Generate a list of integer samples from a Gaussian distribution."""
    samples = np.round(np.random.normal(loc=mean, scale=std, size=num_samples)).astype(int)
    samples = np.clip(samples, a_min=1, a_max=None)
    return samples.tolist()

# Generate and print the samples
gaussian_int_samples = generate_gaussian_int_samples()

for user_sample in gaussian_int_samples:
    coordinates_per_batch_of_users = [(random.uniform(-32, 32), random.uniform(-32, 32)) for i in range(user_sample)]
    percentage_of_proximity = get_proximity_per_worker([NODE_NAME], [NODE_COORDINATES], coordinates_per_batch_of_users)
    migration_cost = 100-percentage_of_proximity[0][1]
    replicas = 2
    for i in range(user_sample):
        user_coordinates = coordinates_per_batch_of_users[i]
        data_size = random.randint(DATA_SIZE_MIN, DATA_SIZE_MAX)
        distance_to_node = calculate_distance(user_coordinates, NODE_COORDINATES)
        result = simulation(f"user-{i}", user_coordinates, data_size, distance_to_node, replicas, migration_cost)
        print(result)
        print("********")
    time.sleep(60*5)


