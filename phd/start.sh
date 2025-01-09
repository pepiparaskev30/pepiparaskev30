#!/bin/bash

# Start the data generator and processor scripts in parallel
python3 data_generation.py &
python3 main.py &

# Wait for both scripts to finish (if needed)
wait
