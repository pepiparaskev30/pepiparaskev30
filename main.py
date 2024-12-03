from fastapi import FastAPI

# Create an instance of FastAPI
app = FastAPI()

# Define a route that takes a 'name' as a query parameter
@app.get("/hello")
def read_hello(name: str):
    return {"message": f"Hello {name}!"}
