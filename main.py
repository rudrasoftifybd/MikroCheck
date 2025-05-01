from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import routeros_api
import subprocess
import socket
from typing import Optional
import time

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection pool (in-memory for demo; use Redis in production)
mikrotik_connections = {}

# --- Helper Functions ---
def ping_ip(ip: str) -> dict:
    """Ping with timeout handling."""
    try:
        result = subprocess.run(
            ["ping", "-c", "4", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout if result.returncode == 0 else f"Ping failed: {result.stderr}"
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Timeout: No response after 8 seconds"}
    except Exception as e:
        return {"success": False, "output": f"Error: {str(e)}"}

# --- API Routes ---
@app.get("/ping")
async def api_ping(ip: str):
    return ping_ip(ip)

@app.get("/check-port")
async def api_check_port(ip: str, port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex((ip, port))
        return {"open": result == 0}
    except socket.timeout:
        return {"open": False, "error": "Timeout"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        sock.close()

@app.post("/connect")
async def api_connect(request: Request):
    try:
        data = await request.json()
        ip = data["ip"]
        port = data.get("port", 8728)
        username = data["username"]
        password = data["password"]

        # Validate input
        if not all([ip, username, password]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Connect to MikroTik
        try:
            connection = routeros_api.RouterOsApiPool(
                ip,
                username=username,
                password=password,
                port=port,
                plaintext_login=True,
                timeout=10
            )
            api = connection.get_api()  # Test connection
            mkt_id = f"{ip}:{port}:{int(time.time())}"
            mikrotik_connections[mkt_id] = connection
            return {"success": True, "connection_id": mkt_id}
        except routeros_api.RouterOsApiConnectionError as e:
            raise HTTPException(status_code=401, detail="Invalid credentials or unreachable")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Connection error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system-info")
async def api_system_info(connection_id: str):
    if connection_id not in mikrotik_connections:
        raise HTTPException(status_code=404, detail="Connection expired or invalid")

    try:
        api = mikrotik_connections[connection_id].get_api()
        sys_info = api.get_resource("/system/resource").get()[0]
        identity = api.get_resource("/system/identity").get()[0]["name"]
        return {
            "identity": identity,
            "cpu": sys_info["cpu-load"],
            "memory": f"{sys_info['free-memory']}/{sys_info['total-memory']}",
            "uptime": sys_info["uptime"],
            "version": sys_info["version"],
            "board": sys_info.get("board-name", "N/A")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch info: {str(e)}")