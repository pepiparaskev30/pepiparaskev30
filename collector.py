import time
import multiprocessing

def generate_data(q):
    i = 0
    while True:
        data = f"Data {i}"
        print(f"Generating: {data}")
        q.put(data)
        i += 1
        time.sleep(1)  # Simulate delay in data generation

if __name__ == "__main__":
    # Create a Queue that can be shared between processes
    q = multiprocessing.Queue()

    # Start the producer process that generates data
    producer = multiprocessing.Process(target=generate_data, args=(q,))
    producer.daemon = True  # Allow the producer to exit when the main program exits
    producer.start()

    # Keep the main process alive to let the producer run indefinitely
    print("Producer started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)  # Main thread sleeps while the producer runs indefinitely
    except KeyboardInterrupt:
        print("Producer stopped.")
