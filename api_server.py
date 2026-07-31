"""
REST API Server Bridge for FoodMaster Auto Open & Auto Close Bot
Compatible with Web Dashboard (/home/asya/Downloads/get menu outlet/web/)
Port: 18800 (default)
Auth Header: X-API-Key: foodmaster-secret-api-key-2026
Run with Uvicorn: uvicorn api_server:app --host 0.0.0.0 --port 18800 --reload
Or directly: python api_server.py
"""

import os
import sys
import json
import threading
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.logger import get_logger
from common.data_provider import DataProviderFactory, OutletData
from common.db_manager import DatabaseManager
from modules.shopee.force_open.refactored import run_force_open

log = get_logger("api_server")

API_PORT = int(os.environ.get("API_PORT", 18800))
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "foodmaster-secret-api-key-2026")

app = FastAPI(
    title="FoodMaster Auto Open & Auto Close Bot API",
    description="REST API Server bridge compatible with Vercel Web Dashboard",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_api_key(request: Request, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    if not API_SECRET_KEY:
        return True

    client_key = x_api_key or request.headers.get("x-api-key")
    if client_key and client_key.strip() == API_SECRET_KEY.strip():
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized. Invalid X-API-Key"
    )


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "FoodMaster Bot API Server"
    }


@app.get("/api/outlets", dependencies=[Depends(verify_api_key)])
async def get_outlets():
    try:
        provider = DataProviderFactory.create_provider()
        outlets = provider.fetch_all_outlets()
        result = []
        for o in outlets:
            item = o.to_dict()
            desired_status, reason = o.calculate_desired_shopee_status()
            item["desired_status"] = "OPEN" if desired_status else "OFF"
            item["priority_reason"] = reason
            result.append(item)
        return result
    except Exception as e:
        log.error(f"API Error fetching outlets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions", dependencies=[Depends(verify_api_key)])
async def get_sessions():
    try:
        profile_path = os.environ.get(
            "SHOPEE_SELENIUM_PROFILE_PATH",
            os.path.join(PROJECT_ROOT, "chromeprofile")
        )
        has_session = os.path.exists(profile_path) and len(os.listdir(profile_path)) > 0

        provider = DataProviderFactory.create_provider()
        outlets = provider.fetch_all_outlets()

        sessions_data = []
        for o in outlets:
            sessions_data.append({
                "store_id": o.store_id,
                "merchant_name": o.portal_name or o.outlet_long_name,
                "nama_resto_final": o.outlet_long_name,
                "nama_outlet": o.outlet_short_name,
                "platform": "shopee",
                "has_session": has_session,
                "phone": o.merchant_id,
                "last_login": o.last_checked_at or datetime.now().isoformat()
            })
        return sessions_data
    except Exception as e:
        log.error(f"API Error fetching sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs", dependencies=[Depends(verify_api_key)])
@app.get("/api/audit-logs", dependencies=[Depends(verify_api_key)])
async def get_logs():
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bot_logs ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()
            logs = [dict(row) for row in rows]
        return logs
    except Exception as e:
        log.error(f"API Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/toggle", dependencies=[Depends(verify_api_key)])
async def post_toggle(payload: Dict[str, Any]):
    store_id = str(payload.get("store_id", ""))
    new_toggle = bool(payload.get("vercel_toggle", True))
    if not store_id:
        raise HTTPException(status_code=400, detail="Missing 'store_id' parameter")

    try:
        provider = DataProviderFactory.create_provider()
        success = provider.update_vercel_toggle(store_id, new_toggle)
        # Safely trigger background cycle
        threading.Thread(
            target=run_force_open,
            kwargs={"data_provider": provider, "dry_run": True},
            daemon=True
        ).start()
        return {
            "status": "success",
            "store_id": store_id,
            "vercel_toggle": new_toggle,
            "message": "Vercel toggle updated and store sync triggered."
        }
    except Exception as e:
        log.error(f"Error processing /api/toggle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/outlets/update", dependencies=[Depends(verify_api_key)])
async def update_outlet_endpoint(payload: Dict[str, Any]):
    store_id = str(payload.get("store_id", ""))
    if not store_id:
        raise HTTPException(status_code=400, detail="Missing 'store_id' parameter")

    try:
        provider = DataProviderFactory.create_provider()
        success = provider.update_outlet(store_id, payload)
        return {
            "status": "success" if success else "not_found",
            "store_id": store_id,
            "message": "Outlet details updated successfully" if success else "Outlet store_id not found"
        }
    except Exception as e:
        log.error(f"Error processing /api/outlets/update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trigger-sync", dependencies=[Depends(verify_api_key)])
async def trigger_sync(payload: Dict[str, Any] = None):
    try:
        body = payload or {}
        dry_run = bool(body.get("dry_run", True))
        provider = DataProviderFactory.create_provider()
        stats = run_force_open(data_provider=provider, dry_run=dry_run)
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }
    except Exception as e:
        log.error(f"Error processing /api/trigger-sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def run_api_server(port: int = API_PORT):
    """Starts the REST API HTTP server using Uvicorn."""
    log.info(f"🌐 REST API Server running on port {port} (X-API-Key: {API_SECRET_KEY})...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    run_api_server()
