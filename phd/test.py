import time
import json, os
from utilities import gather_metrics_for_15_seconds
from multiprocessing import Process, Queue, Event

NODE_NAME = os.getenv("NODE_NAME")
# Function to gather metrics

def gather_metrics(queue, event):
    print("[Gather Metrics] Started...", flush=True)
    metrics_buffer = []  # Buffer to hold collected metrics

    while True:
        # Simulate metrics collection
        data = gather_metrics_for_15_seconds(NODE_NAME)
        metrics_buffer.append(data)
        print(f"[Gather Metrics] Collected: {data}", flush=True)
        time.sleep(3)  # Simulate collection interval

        # Check if the processor is ready for the next batch
        if event.is_set():
            print("[Gather Metrics] Sending data to processor...")
            queue.put(metrics_buffer)  # Send all collected metrics to the processor
            metrics_buffer = []  # Clear the buffer after sending
            event.clear()  # Wait for the next signal to send data

# Function to process data
def process_data(queue, event):
    print("[Process Data] Started...")
    while True:
        if not queue.empty():
            # Retrieve the batch of data from the queue
            data_batch = queue.get()
            print(f"[Process Data] Received data batch: {data_batch}")
            
            # Simulate data processing
            print("[Process Data] Processing data...")
            time.sleep(5)  # Simulate processing time
            print("[Process Data] Finished processing.")
            
            # Signal the gatherer to send the next batch
            event.set()
        else:
            print("[Process Data] Waiting for data...")
            time.sleep(2)

# Main function to start the processes
if __name__ == "__main__":
    queue = Queue()  # Shared queue for data transfer
    event = Event()  # Event for signaling between processes

    # Start the Gather Metrics process
    gather_process = Process(target=gather_metrics, args=(queue, event))
    gather_process.start()

    # Start the Process Data process
    process_process = Process(target=process_data, args=(queue, event))
    process_process.start()

    # Initially signal the gatherer to send the first batch
    event.set()

    # Wait for both processes to finish (infinite loop here, so this won't exit)
    gather_process.join()
    process_process.join()
