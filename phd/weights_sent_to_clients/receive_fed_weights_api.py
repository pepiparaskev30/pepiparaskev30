from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.param_functions import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os
import json
import uvicorn
from datetime import datetime
from utilities import delete_file


app = FastAPI()

global AGGREGATED_JSON_FILES
# Specify the directory and file names
AGGREGATED_JSON_FILES = "/app/aggregated_json_files"
cpu_file_name = "/app/aggregated_json_files/cpu_weights_aggregated.json"
mem_file_name = "/app/aggregated_json_files/mem_weights_aggregated.json"


class FileTypeRequest(BaseModel):
    file_type: str

def get_file_content(file_path):
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            try:

                # Read the content of the JSON file
                with open(file_path, 'r') as json_file:
                    json_data = json.load(json_file)
                delete_file(file_path)
                print("file deleted")
                return JSONResponse(content=json_data, status_code=200)
            except:
                print("File not found")
        else:
            print(f"[ERROR]: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/get_aggregated_json_weights")
def get_json_file(request: FileTypeRequest):
    if request.file_type.lower().startswith("cpu"):
        return get_file_content(cpu_file_name)
    elif request.file_type.lower().startswith("mem"):
        return get_file_content(mem_file_name)
    else:
        raise HTTPException(status_code=400, detail="Invalid file type. Use 'cpu' or 'mem'.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)