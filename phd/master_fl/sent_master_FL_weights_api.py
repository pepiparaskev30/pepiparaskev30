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


from utilities import append_to_csv_nodes
from fastapi import FastAPI, File, Form
from fastapi.responses import JSONResponse
from fastapi import UploadFile
import uvicorn, os, traceback


global MASTER_WEIGHTS_RECEIVE_DIR
global NODE_NOTBOOK_DIR  

# useful env variables
MASTER_WEIGHTS_RECEIVE_DIR = "./master_received_weights_json"
NODE_NOTBOOK_DIR = "./node_notebook"

# Application's main functionality
app = FastAPI()

@app.post("/upload_weights_fdl_master")
async def upload_file(
    file: UploadFile = File(...),
    target_name: str = Form(...),
    node_name: str = Form(...)
):
    try:
        # Handle the uploaded file
        contents = await file.read()
        with open(f"{MASTER_WEIGHTS_RECEIVE_DIR}/weights_{target_name}_{node_name}.json", "wb") as f:
            f.write(contents)
    except Exception as e:
        print(f"Error processing request: {e}")
        traceback.print_exc()
        raise
    
    append_to_csv_nodes(os.path.join(NODE_NOTBOOK_DIR, "nodes_notebook.csv"), node_name)


    return JSONResponse(content={"message": "File and node name uploaded successfully to the master node"}, status_code=200)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)