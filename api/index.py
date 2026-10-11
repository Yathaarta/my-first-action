from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# 1. Enable CORS so any website (any origin) can ping your endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"], 
    allow_headers=["*"],
)

# 2. Define what the incoming POST request body looks like
class QueryData(BaseModel):
    regions: list[str]
    threshold_ms: float

# 3. Load the JSON data into a Pandas DataFrame
# We check a couple of paths just to be safe with how Vercel structures its folders
file_path = "q-vercel-latency.json" if os.path.exists("q-vercel-latency.json") else "../q-vercel-latency.json"
df = pd.read_json(file_path)

# 4. Create the POST endpoint
@app.post("/")
def get_metrics(query: QueryData):
    results = {}
    
    # Loop through the regions they ask for (e.g., "emea", "apac")
    for region in query.regions:
        
        # Filter the dataframe to only look at rows for this specific region
        region_data = df[df['region'] == region]
        
        if len(region_data) == 0:
            continue
            
        # Calculate the requested metrics
        avg_lat = region_data['latency'].mean()
        p95_lat = region_data['latency'].quantile(0.95)
        avg_up = region_data['uptime'].mean()
        breaches = (region_data['latency'] > query.threshold_ms).sum()
        
        # Save them into our results dictionary
        results[region] = {
            "avg_latency": float(avg_lat),
            "p95_latency": float(p95_lat),
            "avg_uptime": float(avg_up),
            "breaches": int(breaches)
        }
        
    return results
