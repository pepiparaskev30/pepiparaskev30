import requests

def send_post_request():
    url = "http://192.168.67.2/api/cpu_latency"
    data = {"num_users": 20}

    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    send_post_request()
