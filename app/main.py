from datetime import datetime, timezone
from enum import Enum

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Incident Tracker API")


# ---------- Модели (что принимаем и что отдаём) ----------

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class EventCreate(BaseModel):
    source: str          # откуда событие, например "ssh-server-01"
    type: str            # тип, например "failed_login"
    severity: Severity


class Event(EventCreate):
    id: int
    created_at: datetime
    incident_id: int | None = None


class IncidentCreate(BaseModel):
    title: str
    assignee: str | None = None


class IncidentUpdate(BaseModel):
    title: str | None = None
    status: IncidentStatus | None = None
    assignee: str | None = None


class Incident(IncidentCreate):
    id: int
    status: IncidentStatus = IncidentStatus.open


class LinkEvent(BaseModel):
    event_id: int


# ---------- Временная "база данных" в памяти ----------

events: dict[int, Event] = {}
incidents: dict[int, Incident] = {}
next_event_id = 1
next_incident_id = 1


def get_incident_or_404(incident_id: int) -> Incident:
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents[incident_id]


# ---------- Health ----------

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


# ---------- Events ----------

# 1. создать событие → 201
@app.post("/api/v1/events", status_code=status.HTTP_201_CREATED)
async def create_event(data: EventCreate) -> Event:
    global next_event_id
    event = Event(id=next_event_id, created_at=datetime.now(timezone.utc), **data.model_dump())
    events[event.id] = event
    next_event_id += 1
    return event


# 2. список событий, фильтр ?severity=high → 200
@app.get("/api/v1/events")
async def list_events(severity: Severity | None = None) -> list[Event]:
    result = list(events.values())
    if severity:
        result = [e for e in result if e.severity == severity]
    return result


# ---------- Incidents ----------

# 3. создать инцидент → 201
@app.post("/api/v1/incidents", status_code=status.HTTP_201_CREATED)
async def create_incident(data: IncidentCreate) -> Incident:
    global next_incident_id
    incident = Incident(id=next_incident_id, **data.model_dump())
    incidents[incident.id] = incident
    next_incident_id += 1
    return incident


# 4. список инцидентов → 200
@app.get("/api/v1/incidents")
async def list_incidents(status: IncidentStatus | None = None) -> list[Incident]:
    result = list(incidents.values())
    if status:
        result = [i for i in result if i.status == status]
    return result


# 5. один инцидент → 200 или 404
@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: int) -> Incident:
    return get_incident_or_404(incident_id)


# 6. изменить инцидент (в том числе статус) → 200
@app.patch("/api/v1/incidents/{incident_id}")
async def update_incident(incident_id: int, data: IncidentUpdate) -> Incident:
    incident = get_incident_or_404(incident_id)
    updated = incident.model_copy(update=data.model_dump(exclude_unset=True))
    incidents[incident_id] = updated
    return updated


# 7. удалить инцидент → 204
@app.delete("/api/v1/incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(incident_id: int):
    get_incident_or_404(incident_id)
    del incidents[incident_id]
    for e in events.values():
        if e.incident_id == incident_id:
            e.incident_id = None


# 8. привязать событие к инциденту → 200
@app.post("/api/v1/incidents/{incident_id}/events")
async def link_event(incident_id: int, data: LinkEvent) -> Event:
    get_incident_or_404(incident_id)
    if data.event_id not in events:
        raise HTTPException(status_code=404, detail="Event not found")
    events[data.event_id].incident_id = incident_id
    return events[data.event_id]


# 9. все события инцидента → 200
@app.get("/api/v1/incidents/{incident_id}/events")
async def list_incident_events(incident_id: int) -> list[Event]:
    get_incident_or_404(incident_id)
    return [e for e in events.values() if e.incident_id == incident_id]