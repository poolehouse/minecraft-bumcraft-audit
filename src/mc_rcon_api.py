#!/usr/bin/env python3
"""
Minecraft RCON HTTP API
Direct HTTP → RCON proxy for executing commands.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel, Field

import httpx
from mcrcon import MCRcon
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Configuration
RCON_HOST = os.getenv("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "CHANGE_ME")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-coder-next")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8090"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mc-rcon-api")

# Global state
rcon_client: Optional[MCRcon] = None
http_client: Optional[httpx.AsyncClient] = None


def connect_rcon() -> MCRcon:
    """Create and connect RCON client."""
    global rcon_client
    if rcon_client:
        try:
            rcon_client.disconnect()
        except Exception:
            pass
    rcon_client = MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT)
    rcon_client.connect()
    logger.info(f"RCON connected to {RCON_HOST}:{RCON_PORT}")
    return rcon_client


def get_rcon() -> MCRcon:
    """Get or create RCON connection."""
    global rcon_client
    if rcon_client is None:
        return connect_rcon()
    # Test connection
    try:
        rcon_client.command("list")
        return rcon_client
    except Exception:
        logger.warning("RCON connection lost, reconnecting...")
        return connect_rcon()


async def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=300.0)
    return http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    global rcon_client, http_client
    logger.info("Starting Minecraft RCON API...")
    try:
        connect_rcon()
        http_client = httpx.AsyncClient(timeout=300.0)
    except Exception as e:
        logger.error(f"Startup failed: {e}")
    yield
    logger.info("Shutting down...")
    if rcon_client:
        try:
            rcon_client.disconnect()
        except Exception:
            pass
    if http_client:
        await http_client.aclose()


app = FastAPI(title="Minecraft RCON API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class CommandRequest(BaseModel):
    command: str = Field(..., description="Minecraft command to execute (without leading /)")
    wait_for_response: bool = Field(True, description="Wait for command output")


class CommandResponse(BaseModel):
    success: bool
    command: str
    response: str
    error: Optional[str] = None


class BuildRequest(BaseModel):
    prompt: str = Field(..., description="Natural language build request")
    player: str = Field("Player", description="Player name for notifications")
    execute: bool = Field(True, description="Execute commands immediately")
    max_commands: int = Field(50, description="Maximum commands to generate")


class BuildResponse(BaseModel):
    success: bool
    prompt: str
    commands: list[str]
    executed: list[CommandResponse]
    error: Optional[str] = None


# Ollama query
async def query_ollama(prompt: str, system_prompt: str) -> str:
    """Query Ollama for command generation."""
    client = await get_http_client()
    try:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 8192
            },
            timeout=600.0  # 10 minute timeout for complex builds
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        logger.error("Ollama query timed out after 10 minutes")
        raise HTTPException(status_code=504, detail="Ollama timeout - try a simpler build or use execute=false to get commands only")
    except Exception as e:
        logger.error(f"Ollama query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ollama error: {e}")


def parse_commands(response: str) -> list[str]:
    """Parse JSON array of commands from response."""
    import json
    import re
    try:
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                commands = json.loads(json_str)
                if isinstance(commands, list):
                    return [cmd for cmd in commands if isinstance(cmd, str) and cmd.startswith("/")]
            except json.JSONDecodeError:
                # Try to fix truncated JSON
                in_string = False
                escaped = False
                last_valid = -1
                for i, char in enumerate(json_str):
                    if char == '"' and not escaped:
                        in_string = not in_string
                        if not in_string:
                            last_valid = i
                    elif char == '\\' and not escaped:
                        escaped = True
                        continue
                    escaped = False
                if last_valid > 0:
                    fixed = json_str[:last_valid + 1] + "]"
                    try:
                        commands = json.loads(fixed)
                        if isinstance(commands, list):
                            return [cmd for cmd in commands if isinstance(cmd, str) and cmd.startswith("/")]
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.error(f"Failed to parse commands: {e}")
    return []


# System prompt for build commands
BUILD_SYSTEM_PROMPT = (
    "You are a Minecraft building assistant. Output ONLY a JSON array of /commands "
    "using ~ ~ ~ relative coords. Use /fill for volumes. Max 50 commands. "
    "Remove: [\"/fill ~-10 ~-5 ~-10 ~10 ~10 ~10 minecraft:air\"]"
    "\n\nIMPORTANT: Keep responses under 8000 tokens. Use /fill for volumes, not individual /setblock calls."
)


# API Endpoints
@app.get("/health")
async def health():
    """Health check."""
    try:
        get_rcon().command("list")
        return {"status": "healthy", "rcon": "connected"}
    except Exception as e:
        return {"status": "degraded", "rcon": "disconnected", "error": str(e)}


@app.post("/command", response_model=CommandResponse)
async def execute_command(req: CommandRequest):
    """Execute a single RCON command."""
    try:
        rcon = get_rcon()
        cmd = req.command if req.command.startswith("/") else f"/{req.command}"
        response = rcon.command(cmd) if req.wait_for_response else ""
        return CommandResponse(success=True, command=cmd, response=response)
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return CommandResponse(success=False, command=req.command, response="", error=str(e))


@app.post("/commands")
async def execute_commands(commands: list[str]):
    """Execute multiple commands sequentially."""
    results = []
    for cmd in commands:
        try:
            rcon = get_rcon()
            full_cmd = cmd if cmd.startswith("/") else f"/{cmd}"
            response = rcon.command(full_cmd)
            results.append({"command": full_cmd, "response": response, "success": True})
            await asyncio.sleep(0.05)
        except Exception as e:
            results.append({"command": cmd, "response": "", "success": False, "error": str(e)})
    return {"results": results}


@app.post("/build", response_model=BuildResponse)
async def build(req: BuildRequest):
    """Generate and optionally execute build commands from natural language."""
    try:
        # Query Ollama for commands
        response = await query_ollama(req.prompt, BUILD_SYSTEM_PROMPT)
        commands = parse_commands(response)
        
        if not commands:
            return BuildResponse(
                success=False,
                prompt=req.prompt,
                commands=[],
                executed=[],
                error="No valid commands generated"
            )
        
        # Limit commands
        commands = commands[:req.max_commands]
        
        executed = []
        if req.execute:
            rcon = get_rcon()
            # Notify player
            if req.player:
                try:
                    rcon.command(f"/tellraw {req.player} {{\"text\":\"Building {len(commands)} commands...\",\"color\":\"green\"}}")
                except Exception:
                    pass
            
            for cmd in commands:
                try:
                    response = rcon.command(cmd)
                    executed.append(CommandResponse(success=True, command=cmd, response=response))
                    await asyncio.sleep(0.05)
                except Exception as e:
                    executed.append(CommandResponse(success=False, command=cmd, response="", error=str(e)))
            
            # Report results
            if req.player:
                success_count = sum(1 for e in executed if e.success)
                try:
                    rcon.command(f"/tellraw {req.player} {{\"text\":\"Done! {success_count}/{len(commands)} commands succeeded.\",\"color\":\"gold\"}}")
                except Exception:
                    pass
        
        return BuildResponse(
            success=True,
            prompt=req.prompt,
            commands=commands,
            executed=executed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build failed: {e}")
        return BuildResponse(
            success=False,
            prompt=req.prompt,
            commands=[],
            executed=[],
            error=str(e)
        )


@app.post("/clear")
async def clear_area(size: int = 20, player: str = "Player"):
    """Clear an area around the player (fill with air)."""
    cmd = f"/fill ~-{size//2} ~-5 ~-{size//2} ~{size//2} ~{size//2} ~{size//2} minecraft:air"
    try:
        rcon = get_rcon()
        response = rcon.command(cmd)
        if player:
            rcon.command(f"/tellraw {player} {{\"text\":\"Cleared {size}x{size} area.\",\"color\":\"gold\"}}")
        return {"success": True, "command": cmd, "response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)