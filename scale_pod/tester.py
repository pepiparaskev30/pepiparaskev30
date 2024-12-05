import requests
import json

# Replace with the appropriate URL to your Minikube service
url = "http://192.168.49.2<node-port>/scale"

# Define the payload for the POST request
payload = {
    "action": "scale",
    "prefix": "s1",  # Example prefix
    "namespace": "default",
    "replicas": 3
}

# Send the POST request to the FastAPI endpoint
response = requests.post(url, json=payload)

# Print the response from the API
if response.status_code == 200:
    print("Response:", response.json())
else:
    print(f"Error: {response.status_code}, {response.text}")
