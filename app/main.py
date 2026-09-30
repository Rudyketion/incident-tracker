from fastapi import FastAPI, HTTPException

app = FastAPI(title="Incident Tracker API")

# временная "база" в памяти
incidents = {
    1: {"id": 1, "title": "Brute force на SSH", "status": "open"},
}

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}

@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: int):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents[incident_id]