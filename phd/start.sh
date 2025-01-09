#!/bin/bash

# Start the data generator and processor scripts with unbuffered output
python3 -u data_generation.py > /proc/1/fd/1 2>/proc/1/fd/2 &
python3 -u main.py > /proc/1/fd/1 2>/proc/1/fd/2 &

# Wait for both scripts to finish
wait
