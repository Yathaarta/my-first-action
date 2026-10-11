```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).with_name("q-vercel-latency.json")


def percentile95(values):
    values = sorted(values)
    position = (len(values) - 1) * 0.95
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


@app.api_route("/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def analytics(request: Request, path: str):
    if request.method == "OPTIONS":
        return JSONResponse({"status": "ok"})

    if request.method == "GET":
        return {"message": "Send a POST request to this endpoint."}

    try:
        body = await request.json()
        regions = body.get("regions", ["emea", "apac"])
        threshold_ms = float(body.get("threshold_ms", 180))

        if not isinstance(regions, list):
            return JSONResponse({"error": "regions must be a list"}, status_code=400)

        if not DATA_FILE.is_file():
            return JSONResponse({"error": "Telemetry dataset not found"}, status_code=500)

        with DATA_FILE.open(encoding="utf-8") as f:
            records = json.load(f)

        results = {}

        for region in regions:
            rows = [r for r in records if r["region"].lower() == str(region).lower()]
            if not rows:
                continue

            latencies = [float(r["latency_ms"]) for r in rows]
            uptimes = [float(r["uptime_pct"]) for r in rows]

            results[region] = {
                "avg_latency": sum(latencies) / len(latencies),
                "p95_latency": percentile95(latencies),
                "avg_uptime": sum(uptimes) / len(uptimes),
                "breaches": sum(latency > threshold_ms for latency in latencies),
            }

        return {"regions": results}

    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
```
