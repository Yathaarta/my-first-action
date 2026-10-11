from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route("/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def catch_all(request: Request, path: str):
    if request.method == "OPTIONS":
        return JSONResponse(content={"status": "ok"})

    if request.method == "POST":
        try:
            body_bytes = await request.body()
            body = json.loads(body_bytes) if body_bytes else {}
            regions = body.get("regions", ["emea", "apac"])
            threshold_ms = body.get("threshold_ms", 180)

            # Find the file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "q-vercel-latency.json"),
                os.path.join(base_dir, "q-vercel-latency.json"),
                "q-vercel-latency.json",
                "api/q-vercel-latency.json"
            ]
            
            file_path = None
            for p in possible_paths:
                if os.path.exists(p) and os.path.getsize(p) > 0:
                    file_path = p
                    break
            
            if not file_path:
                return JSONResponse(content={"error": "File completely missing from Vercel build."}, status_code=500)

            # 1. BYPASS PANDAS: Open the file with native Python
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
            except Exception as e:
                return JSONResponse(content={"error": f"Failed to open file: {str(e)}"}, status_code=500)

            # 2. Parse the JSON safely (Handles normal JSON & JSON Lines)
            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError:
                try:
                    lines = raw_content.strip().split('\n')
                    data = [json.loads(line) for line in lines if line.strip()]
                except Exception:
                    # IF IT FAILS, PRINT THE FILE CONTENTS SO WE CAN SEE WHAT'S WRONG!
                    snippet = raw_content[:150]
                    return JSONResponse(content={"error": f"File is not valid JSON! It looks like this: {snippet}"}, status_code=500)

            # 3. Now let Pandas do the math
            df = pd.DataFrame(data)
            df.columns = [str(c).lower() for c in df.columns]
            
            if 'region' not in df.columns:
                return JSONResponse(content={"error": f"Missing 'region' column. I see: {list(df.columns)}"}, status_code=500)
                
            df['region'] = df['region'].astype(str).str.lower()

            results = {}
            for r in regions:
                target = str(r).lower()
                region_data = df[df['region'] == target]
                
                if not region_data.empty:
                    results[r] = {
                        "avg_latency": float(region_data['latency'].mean()),
                        "p95_latency": float(region_data['latency'].quantile(0.95)),
                        "avg_uptime": float(region_data['uptime'].mean()),
                        "breaches": int((region_data['latency'] > threshold_ms).sum())
                    }
                else:
                    results[r] = {
                        "avg_latency": 0.0,
                        "p95_latency": 0.0,
                        "avg_uptime": 0.0,
                        "breaches": 0
                    }
            return JSONResponse(content=results)

        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
            
    return JSONResponse(content={"message": "Server is awake and ready!"})
