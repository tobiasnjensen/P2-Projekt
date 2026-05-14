"""
Drone Detection API — FastAPI + PostgreSQL
Schema:
    devices:   id, mac_adresse, last_seen
    positions: id, device_id, x, y, z, timestamp

Install:
    pip install fastapi uvicorn asyncpg python-dotenv

Run:
    py -m uvicorn drone_api:app --reload --port 8000
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Drone Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Change these to your actual table names if different ──────────────────────
DEVICES_TABLE   = "device"
POSITIONS_TABLE = "positions"
# ─────────────────────────────────────────────────────────────────────────────


async def get_db():
    return await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "DroneDatabase"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Spatomando"),
    )


@app.get("/drones")
async def list_drones():
    """
    Returns every drone with its most recent position.
    The dashboard calls this on load and every 3 seconds.
    """
    db = await get_db()
    try:
        rows = await db.fetch(f"""
            SELECT
                d.id,
                d.mac_adresse,
                d.last_seen     AS first_seen,
                p.x,
                p.y,
                p.z,
                p.timestamp     AS last_seen
            FROM {DEVICES_TABLE} d
            LEFT JOIN LATERAL (
                SELECT x, y, z, timestamp
                FROM {POSITIONS_TABLE}
                WHERE device_id = d.id
                ORDER BY timestamp DESC
                LIMIT 1
            ) p ON true
            ORDER BY d.id
        """)
        return [dict(r) for r in rows]
    finally:
        await db.close()


@app.get("/drones/search")
async def search_drones(
    mac_adresse: Optional[str]      = Query(None),
    from_time:   Optional[datetime] = Query(None),
    to_time:     Optional[datetime] = Query(None),
):
    """
    Filters drones by MAC address and/or time window.
    Returns a list of matching device IDs.
    """
    db = await get_db()
    try:
        query = f"""
            SELECT DISTINCT d.id
            FROM {DEVICES_TABLE} d
            JOIN {POSITIONS_TABLE} p ON p.device_id = d.id
            WHERE 1=1
        """
        params = []

        if mac_adresse:
            params.append(f"%{mac_adresse}%")
            query += f" AND d.mac_adresse ILIKE ${len(params)}"
        if from_time:
            params.append(from_time)
            query += f" AND p.timestamp >= ${len(params)}"
        if to_time:
            params.append(to_time)
            query += f" AND p.timestamp <= ${len(params)}"

        query += " ORDER BY d.id"
        rows = await db.fetch(query, *params)
        return [r["id"] for r in rows]
    finally:
        await db.close()


@app.get("/drones/{device_id}/path")
async def get_flight_path(
    device_id: int,
    from_time: Optional[datetime] = Query(None),
    to_time:   Optional[datetime] = Query(None),
    limit:     int                = Query(500),
):
    """
    Returns the ordered position history for one drone.
    x, y = horizontal position. z = altitude.
    """
    db = await get_db()
    try:
        query = f"""
            SELECT p.x, p.y, p.z, p.timestamp
            FROM {POSITIONS_TABLE} p
            WHERE p.device_id = $1
        """
        params = [device_id]

        if from_time:
            params.append(from_time)
            query += f" AND p.timestamp >= ${len(params)}"
        if to_time:
            params.append(to_time)
            query += f" AND p.timestamp <= ${len(params)}"

        params.append(limit)
        query += f" ORDER BY p.timestamp ASC LIMIT ${len(params)}"

        rows = await db.fetch(query, *params)
        return [dict(r) for r in rows]
    finally:
        await db.close()


@app.get("/bounds")
async def get_bounds():
    """
    Returns min/max x, y, z across all positions.
    Used by the dashboard to auto-scale the map.
    """
    db = await get_db()
    try:
        row = await db.fetchrow(f"""
            SELECT
                MIN(x) AS x_min, MAX(x) AS x_max,
                MIN(y) AS y_min, MAX(y) AS y_max,
                MIN(z) AS z_min, MAX(z) AS z_max
            FROM {POSITIONS_TABLE}
        """)
        return dict(row)
    finally:
        await db.close()
