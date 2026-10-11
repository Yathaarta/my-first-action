from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

class QueryData(BaseModel):
    regions: list[str]
    threshold_ms: float

custom_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}

@app.post("/")
@app.post("/{path:path}")
def get_metrics(query: QueryData, path: str = ""):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "q-vercel-latency.json")
        
        if not os.path.exists(file_path):
            return JSONResponse(content={"error": "JSON file not found!"}, headers=custom_headers)
            
        # 1. First, try reading it as a normal JSON file
        try:
            df = pd.read_json(file_path)
        except ValueError:
            # If that crashes, it's definitely a JSON Lines file
            df = pd.read_json(file_path, lines=True)
            
        # 2. If it loaded normally, but messed up the columns, try JSON Lines again
        if 'latency' not in df.columns:
            try:
                df = pd.read_json(file_path, lines=True)
            except:
                pass
                
        # 3. IF IT STILL CAN'T FIND 'latency', print out the actual columns!
        if 'latency' not in df.columns:
            return JSONResponse(
                content={"error": f"Missing 'latency'. The columns I actually see are: {list(df.columns)}"}, 
                headers=custom_headers
            )

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
            
        return JSONResponse(content=results, headers=custom_headers)

    except Exception as e:
        error_msg = str(e) + "\n" + traceback.format_exc()
        return JSONResponse(content={"error": error_msg}, headers=custom_headers, status_code=500)
