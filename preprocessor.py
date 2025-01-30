from queue import Queue
import os, time
import threading

# Get the scrape interval from the environment variables
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", 1)) # In Seconds


def operations(data):
    time.sleep(10)
    return data

class Gatherer:
    # Flags to check if the threads are ready to collect information
    ready_flag = True

    # Lists to store the results used by CA, RL and GNN
    data_queue = Queue()

    # Amount of time to wait before starting a new thread
    wait_time = int(os.getenv('WAIT_TIME', '10'))


    # Start the threads
    def start_thread():
        # Start a CA thread
        threading.Thread(target=Gatherer.data_).start()

    # Start a CA thread and when it finishes, start another one
    def data_():
        start_time = time.time()
        N = Gatherer.data_queue.qsize()

        data_list = []
        for i in range(N):
            data_list.append(Gatherer.data_queue.get())
        print(data_list)

        Gatherer.ready_flag = False
        operations(data_list)
        Gatherer.ready_flag = True

        end_time = time.time()
        sum_time = end_time - start_time

        # If the time is less than the wait time, sleep for the difference
        if sum_time < Gatherer.wait_time:
            time.sleep(Gatherer.wait_time - sum_time)

        threading.Thread(target=Gatherer.data_).start()
        return
    



Gatherer.start_thread()

while True:
    # Make a Scrape for the whole cluster
    try:
        cluster_sample = {"data": f"data_{time.time()}"}
    except Exception as err:
        print(f"Unexpected Collection Error (But DP Gathering again in {SCRAPE_INTERVAL} seconds). Error: {err=}, {type(err)=}")
        time.sleep(SCRAPE_INTERVAL)
        continue

    Gatherer.data_queue.put(cluster_sample)

    # Add functionallity to export the cluster topology as well from NETMA CRDs

    time.sleep(SCRAPE_INTERVAL)
