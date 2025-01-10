import os, json
import time
import urllib.parse
import requests
from kubernetes import client, config
from utilities import gather_metrics_for_15_seconds
from datetime import datetime
from multiprocessing import Queue
import socket
from datetime import datetime

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
NODE_NAME = os.getenv("NODE_NAME")

HOST = 'localhost'
PORT = 65432

if __name__ == "__main__":
    print("Data Generator started...")

    while True:  # Retry loop for connection
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((HOST, PORT))
                print(f"[Data Generator] Connected to {HOST}:{PORT}")
                
                while True:
                    # Simulate data generation
                    data = gather_metrics_for_15_seconds(NODE_NAME)
                    client_socket.sendall(json.dumps(data).encode('utf-8'))  # Send data
                    print(f"[Data Generator] Sent data: {data}")
                    time.sleep(5)
        except ConnectionRefusedError:
            print("[Data Generator] Connection refused. Retrying in 5 seconds...")
            time.sleep(5)  # Wait before retrying
