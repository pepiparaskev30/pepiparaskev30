import requests
import threading
import time
import random
import numpy as np

# API endpoint
API_URL = "http://192.168.67.2:8003/simulate"

# Simulation duration
DURATION_SECONDS = 10

# Gaussian distribution parameters
MEAN_USERS = 200
STD_DEV = 70
MIN_USERS = 30
MAX_USERS = 500

# Function to send one POST request
def send_request(num_users, load_type):
    try:
        response = requests.post(API_URL, json={
            "num_requests": num_users,
            "load_type": load_type
        })
        print(f"[{load_type.upper()}] Users: {num_users}, Status: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

# Start simulation
def simulate():
    end_time = time.time() + DURATION_SECONDS

    while time.time() < end_time:
        # Generate number of users from Gaussian and clip to [MIN, MAX]
        num_users = int(np.clip(np.random.normal(MEAN_USERS, STD_DEV), MIN_USERS, MAX_USERS))
        load_type = random.choice(["cpu", "memory"])

        thread = threading.Thread(target=send_request, args=(num_users, load_type))
        thread.start()

        # Small delay between launching requests
        time.sleep(0.2)  # ~5 requests per second

if __name__ == "__main__":
    simulate()
