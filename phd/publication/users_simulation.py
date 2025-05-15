import requests
import threading
import time
import random
import numpy as np

# API endpoint (replace with your real Ingress domain if needed)
API_URL = "http://example.com/simulate"

# Simulation duration in seconds
DURATION_SECONDS = 600

# Gaussian user load parameters
MEAN_USERS = 120
STD_DEV = 70
MIN_USERS = 30
MAX_USERS = 500

# Available load types
LOAD_TYPES = ["cpu", "memory", "network"]

# Function to send one POST request
def send_request(num_users, load_type):
    try:
        response = requests.post(API_URL, json={
            "num_requests": num_users,
            "load_type": load_type
        })
        print(f"[{load_type.upper()}] Users: {num_users}, Status: {response.status_code}")
    except Exception as e:
        print(f"Error sending {load_type} request: {e}")

# Simulation loop
def simulate():
    print(f"Starting load simulation for {DURATION_SECONDS} seconds...")
    end_time = time.time() + DURATION_SECONDS

    while time.time() < end_time:
        # Generate a number of users from Gaussian, clamp to min/max
        num_users = int(np.clip(np.random.normal(MEAN_USERS, STD_DEV), MIN_USERS, MAX_USERS))
        load_type = random.choice(LOAD_TYPES)

        # Start request in a new thread
        thread = threading.Thread(target=send_request, args=(num_users, load_type))
        thread.start()

        time.sleep(10)  # 1.4–3.3 req/sec on average

    print("Simulation completed.")

if __name__ == "__main__":
    simulate()
