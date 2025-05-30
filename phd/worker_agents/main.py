import time
import json, os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from utilities import gather_metrics_for_30_seconds, Gatherer
from multiprocessing import Process, Queue, Event


NODE_NAME = os.getenv("NODE_NAME")
# Get the scrape interval from the environment variables
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", 1)) # In Seconds


# Main function to start the processes
if __name__ == "__main__":

    Gatherer.start_thread()

    while True:
        # Make a Scrape for the whole cluster
        try:
            cluster_sample = gather_metrics_for_30_seconds(NODE_NAME)
        except Exception as err:
            print(f"Unexpected Collection Error (But DP Gathering again in {SCRAPE_INTERVAL} seconds).")
            time.sleep(SCRAPE_INTERVAL)
            continue

        Gatherer.prometheus_data_queue.put(cluster_sample)
        # Add functionallity to export the cluster topology as well from NETMA CRDs

        time.sleep(SCRAPE_INTERVAL)


