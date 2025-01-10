#!/bin/bash

# Run both scripts in parallel
python data_generation.py &
python main.py &

# Wait for both scripts to finish
wait
