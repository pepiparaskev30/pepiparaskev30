#!/usr/bin/env python
'''
# Script: fed_master.py
# Maintainer: Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Role: Lead Developer
# Copyright (c) 2023 Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Licensed under the MIT License.
# Source code development for the PhD thesis 

####################################################################
# Overview:

This code will reside on the master node where the aggregation of the node pre-
trained model weights will be utilized.

The script gathers the weights from the nodes' pre-trained models, performs
aggregation and sends them back to the nodes in order to distribute the global 
training knowledge

'''

# Import necessary libraries
from utilities import append_record_to_csv
from fastapi import FastAPI, File, Form
from fastapi.responses import JSONResponse
from fastapi import UploadFile
import uvicorn, os, traceback

# Define global variables
MASTER_WEIGHTS_RECEIVE_DIR = "/app/master_received_weights_json"
NODE_NOTBOOK_DIR = "/app/nodes_notebook"

# Application's main functionality
app = FastAPI()

@app.post("/upload_weights_fdl_master")
async def upload_file(
    file: UploadFile = File(...),
    target_name: str = Form(...),
    node_name: str = Form(...)
):
    try:
        # Ensure the directory exists before trying to write files
        if not os.path.exists(MASTER_WEIGHTS_RECEIVE_DIR):
            os.makedirs(MASTER_WEIGHTS_RECEIVE_DIR)
        
        # Handle the uploaded file and write it to the appropriate directory
        contents = await file.read()
        file_path = f"{MASTER_WEIGHTS_RECEIVE_DIR}/weights_{target_name}_{node_name}.json"
        with open(file_path, "wb") as f:
            f.write(contents)
        
        print(f"File uploaded and saved to {file_path}")
    except Exception as e:
        print(f"Error processing request: {e}")
        traceback.print_exc()
        raise
    
    notebook_file_path = f"{NODE_NOTBOOK_DIR}"+"/"+"nodes_notebook.csv"
    print(f"Appending node name to {notebook_file_path}", flush=True)
    
    # Append the node name to the CSV file
    append_record_to_csv(notebook_file_path, node_name)

    return JSONResponse(content={"message": "File and node name uploaded successfully to the master node"}, status_code=200)

# Run the application with uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
