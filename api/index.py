from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# 1. Allow all methods so preflight OPTIONS requests don't get blocked
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

class QueryData(BaseModel):
    regions: list[str]
    threshold_ms: float

# File loading logic
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "q-vercel-latency.json")
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
        
    # 2. Forcefully attach the exact CORS headers requested in the forum
    custom_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
    }
    
    return JSONResponse(content=results, headers=custom_headers)
