import time
import json, os
from utilities import gather_metrics_for_15_seconds
from multiprocessing import Process, Queue, Event

NODE_NAME = os.getenv("NODE_NAME")


# Main function to start the processes
if __name__ == "__main__":
    print(gather_metrics_for_15_seconds(NODE_NAME))
