#!/bin/sh

# Start both Python scripts in parallel
python sent_master_FL_weights_api.py & 
python federated_weight_aggregration.py & 

# Wait for both processes to finish
wait
