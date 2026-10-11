from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"], 
    allow_headers=["*"],
)

class QueryData(BaseModel):
    regions: list[str]
    threshold_ms: float

# FOOLPROOF WAY TO FIND THE FILE IN VERCEL
# This gets the exact folder that index.py is sitting in
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "q-vercel-latency.json")

# Load data
df = pd.read_json(file_path)

@app.post("/")
def get_metrics(query: QueryData):
    results = {}
    
    for region in query.regions:
        region_data = df[df['region'] == region]
        
        if len(region_data) == 0:
            continue
            
        avg_lat = region_data['latency'].mean()
        p95_lat = region_data['latency'].quantile(0.95)
        avg_up = region_data['uptime'].mean()
        breaches = (region_data['latency'] > query.threshold_ms).sum()
        
        results[region] = {
            "avg_latency": float(avg_lat),
            "p95_latency": float(p95_lat),
            "avg_uptime": float(avg_up),
            "breaches": int(breaches)
        }
        
    return results
