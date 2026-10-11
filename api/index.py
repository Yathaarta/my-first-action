from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# 1. Standard CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

class QueryData(BaseModel):
    regions: list[str]
    threshold_ms: float

# 2. The exact headers that worked for the student in the forum
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

# 3. Manually catch the invisible OPTIONS preflight check and approve it
@app.options("/")
@app.options("/{path:path}")
def preflight_handler(path: str = ""):
    return Response(headers=CORS_HEADERS)

# 4. Our actual POST endpoint
@app.post("/")
@app.post("/{path:path}")
def get_metrics(query: QueryData, path: str = ""):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "q-vercel-latency.json")
    
    # Safely load the data (handling both standard JSON and JSON Lines formats)
    try:
        df = pd.read_json(file_path)
        if 'latency' not in df.columns:
            df = pd.read_json(file_path, lines=True)
    except:
        df = pd.read_json(file_path, lines=True)
        
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
        
    # Return the math results WITH the mandatory forum headers attached
    return JSONResponse(content=results, headers=CORS_HEADERS)
