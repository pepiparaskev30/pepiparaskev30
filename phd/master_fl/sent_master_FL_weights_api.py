#!/usr/bin/env python
'''
# Script: sent_master_FL_weights_api.py
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

# fedasync_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import numpy as np
import threading
import uvicorn

app = FastAPI()

# Global state per target resource
global_models = {}  # target -> {model, round, client_versions}
alpha = 0.5
lock = threading.Lock()

class ModelUpdate(BaseModel):
    client_id: str
    target_resource: str
    client_model: Dict[str, List[float]]

@app.post("/upload_weights")
def receive_weights(update: ModelUpdate):
    with lock:
        target = update.target_resource
        client_id = update.client_id
        client_weights = {k: np.array(v) for k, v in update.client_model.items()}

        if target not in global_models:
            global_models[target] = {
                "model": {k: np.zeros_like(v) for k, v in client_weights.items()},
                "round": 0,
                "client_versions": {}
            }

        state = global_models[target]
        global_weights = state["model"]
        server_round = state["round"]
        client_round = state["client_versions"].get(client_id, server_round)

        staleness = server_round - client_round
        decay = 1 / (1 + staleness) if staleness >= 0 else 1

        # Apply FedAsync update
        for k in global_weights:
            global_weights[k] = (1 - alpha * decay) * global_weights[k] + (alpha * decay) * client_weights[k]

        state["round"] += 1
        state["client_versions"][client_id] = state["round"]

        return {
            "status": "success",
            "message": f"Update received from {client_id} for {target}",
            "staleness": staleness,
            "decay": round(decay, 3),
            "server_round": state["round"]
        }

@app.get("/global_model/{target}")
def get_model(target: str):
    if target in global_models:
        return {
            "model": {k: v.tolist() for k, v in global_models[target]["model"].items()},
            "server_round": global_models[target]["round"]
        }
    return {"error": "Target not found"}, 404

if __name__ == "__main__":
    uvicorn.run("sent_master_FL_weights_api:app", host="0.0.0.0", port=8002, reload=True)


