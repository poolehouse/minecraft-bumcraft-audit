#!/usr/bin/env python3
"""
Minecraft AI Builder Service
Connects to Minecraft server via RCON, listens for !build commands,
sends prompts to Ollama (qwen3-coder-next), and executes building commands.

Supported chat commands:
  !build <prompt>              - AI-generated build from free-text prompt
  !build preset:halfpipe       - Build a skate halfpipe
  !build preset:streetplaza    - Build a skate street plaza
  !undo                        - Undo the last build (revert blocks to air)
"""

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, List

import httpx
from mcrcon import MCRcon

# Configuration
RCON_HOST = os.getenv("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "CHANGE_ME")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-coder-next")
LOG_FILE = Path(os.getenv("MC_LOG_FILE", "/path/to/minecraft-server-bumcraft/data/logs/latest.log"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mc-ai-builder")

# Undo history: player_name -> list of executed command lists (for undo)
UNDO_HISTORY: Dict[str, List[List[str]]] = {}
MAX_UNDO_ENTRIES = 10

# ---------------------------------------------------------------------------
# Preset build definitions (relative coordinates ~ ~ ~ centered on player)
# ---------------------------------------------------------------------------

PRESETS: Dict[str, List[str]] = {
    "halfpipe": [
        # Quarter-pipe ramp (stone -> smooth stone surface)
        "/fill ~-10 ~-1 ~-5 ~10 ~-1 ~5 minecraft:stone",
        # Transition curve: fill a ramp shape using stacked fills
        "/fill ~-10 ~0 ~-5 ~-10 ~4 ~5 minecraft:stone",
        "/fill ~-9 ~0 ~-5 ~-9 ~3 ~5 minecraft:stone",
        "/fill ~-8 ~0 ~-5 ~-8 ~2 ~5 minecraft:stone",
        "/fill ~-7 ~0 ~-5 ~-7 ~1 ~5 minecraft:stone",
        "/fill ~-6 ~0 ~-5 ~-6 ~0 ~5 minecraft:stone",
        "/fill ~-5 ~0 ~-5 ~-5 ~0 ~5 minecraft:stone",
        "/fill ~-4 ~0 ~-5 ~-4 ~0 ~5 minecraft:stone",
        "/fill ~-3 ~0 ~-5 ~-3 ~0 ~5 minecraft:stone",
        "/fill ~-2 ~0 ~-5 ~-2 ~0 ~5 minecraft:stone",
        "/fill ~-1 ~0 ~-5 ~-1 ~0 ~5 minecraft:stone",
        "/fill ~0 ~0 ~-5 ~0 ~0 ~5 minecraft:stone",
        "/fill ~1 ~0 ~-5 ~1 ~0 ~5 minecraft:stone",
        "/fill ~2 ~0 ~-5 ~2 ~0 ~5 minecraft:stone",
        "/fill ~3 ~0 ~-5 ~3 ~0 ~5 minecraft:stone",
        "/fill ~4 ~0 ~-5 ~4 ~0 ~5 minecraft:stone",
        "/fill ~5 ~0 ~-5 ~5 ~0 ~5 minecraft:stone",
        "/fill ~6 ~0 ~-5 ~6 ~0 ~5 minecraft:stone",
        "/fill ~7 ~0 ~-5 ~7 ~1 ~5 minecraft:stone",
        "/fill ~8 ~0 ~-5 ~8 ~2 ~5 minecraft:stone",
        "/fill ~9 ~0 ~-5 ~9 ~3 ~5 minecraft:stone",
        "/fill ~10 ~0 ~-5 ~10 ~4 ~5 minecraft:stone",
        # Deck / coping
        "/fill ~-10 ~5 ~-5 ~10 ~5 ~5 minecraft:stone_bricks",
        # Smooth skating surface (concrete)
        "/fill ~-10 ~0 ~-5 ~10 ~0 ~5 minecraft:light_gray_concrete",
    ],
    "streetplaza": [
        # Flat plaza base
        "/fill ~-20 ~-1 ~-20 ~20 ~-1 ~20 minecraft:stone",
        "/fill ~-20 ~0 ~-20 ~20 ~0 ~20 minecraft:light_gray_concrete",
        # Ledges
        "/fill ~-15 ~0 ~-10 ~-10 ~1 ~-10 minecraft:stone_bricks",
        "/fill ~10 ~0 ~-10 ~15 ~1 ~-10 minecraft:stone_bricks",
        "/fill ~-15 ~0 ~10 ~-10 ~1 ~10 minecraft:stone_bricks",
        "/fill ~10 ~0 ~10 ~15 ~1 ~10 minecraft:stone_bricks",
        # Stairs (stone brick stairs)
        "/fill ~-12 ~1 ~-8 ~-12 ~2 ~-8 minecraft:stone_brick_stairs",
        "/fill ~-11 ~1 ~-7 ~-11 ~2 ~-7 minecraft:stone_brick_stairs",
        "/fill ~-10 ~1 ~-6 ~-10 ~2 ~-6 minecraft:stone_brick_stairs",
        "/fill ~12 ~1 ~-8 ~12 ~2 ~-8 minecraft:stone_brick_stairs",
        "/fill ~11 ~1 ~-7 ~11 ~2 ~-7 minecraft:stone_brick_stairs",
        "/fill ~10 ~1 ~-6 ~10 ~2 ~-6 minecraft:stone_brick_stairs",
        # Manual pad
        "/fill ~-5 ~0 ~-5 ~5 ~0 ~5 minecraft:gray_concrete",
        # Rail between ledges
        "/fill ~-15 ~2 ~-10 ~15 ~2 ~-10 minecraft:iron_bars",
        "/fill ~-15 ~2 ~10 ~15 ~2 ~10 minecraft:iron_bars",
    ],
}

# ---------------------------------------------------------------------------
# MinecraftAIBuilder
# ---------------------------------------------------------------------------

class MinecraftAIBuilder:
    def __init__(self):
        self.rcon: Optional[MCRcon] = None
        self.last_log_position = 0
        self.http_client = httpx.AsyncClient(timeout=600.0)
        self.running = False

    async def connect_rcon(self) -> bool:
        """Connect to Minecraft RCON."""
        try:
            self.rcon = MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT)
            self.rcon.connect()
            logger.info(f"Connected to Minecraft RCON at {RCON_HOST}:{RCON_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RCON: {e}")
            return False

    def disconnect_rcon(self):
        """Disconnect from RCON."""
        if self.rcon:
            try:
                self.rcon.disconnect()
            except Exception:
                pass
            self.rcon = None

    async def send_command(self, command: str) -> str:
        """Send a command via RCON and return response."""
        if not self.rcon:
            if not await self.connect_rcon():
                return "ERROR: RCON not connected"
        try:
            response = self.rcon.command(command)
            return response
        except Exception as e:
            logger.error(f"RCON command failed: {e}")
            self.disconnect_rcon()
            return f"ERROR: {e}"

    async def query_ollama(self, prompt: str) -> str:
        """Send prompt to Ollama and return response."""
        try:
            response = await self.http_client.post(
                f"{OLLAMA_BASE_URL}/chat/completions",
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a Minecraft building assistant. "
                                "Given a building request, respond with ONLY a JSON array of Minecraft commands "
                                "that will build the requested structure. Use /setblock, /fill, /clone, /structure, "
                                "and other vanilla commands. Coordinates should be relative to the player (~ ~ ~). "
                                "Example format: [\"/setblock ~ ~ ~ minecraft:stone\", \"/fill ~1 ~ ~1 ~5 ~5 ~5 minecraft:diamond_block\"]"
                                "\n\nIMPORTANT: Keep responses under 12000 tokens. For complex builds, return only essential "
                                "structural commands. Use /fill for volumes, not individual /setblock calls. "
                                "Maximum 50 commands per response."
                                "\n\nFor REMOVING structures: use \"/fill ~x ~y ~z ~x2 ~y2 ~z2 minecraft:air\" "
                                "Example: [\"/fill ~-10 ~-5 ~-10 ~10 ~10 ~10 minecraft:air\"]"
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 12288
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama query failed: {e}")
            return f"ERROR: {e}"

    def parse_commands(self, response: str) -> list:
        """Parse JSON array of commands from Ollama response."""
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    commands = json.loads(json_str)
                    if isinstance(commands, list):
                        return [cmd for cmd in commands if isinstance(cmd, str) and cmd.startswith("/")]
                except json.JSONDecodeError:
                    fixed = self._fix_truncated_json(json_str)
                    if fixed:
                        commands = json.loads(fixed)
                        if isinstance(commands, list):
                            valid = [cmd for cmd in commands if isinstance(cmd, str) and cmd.startswith("/")]
                            if valid:
                                logger.info(f"Recovered {len(valid)} commands from truncated response")
                                return valid
        except Exception as e:
            logger.error(f"Failed to parse commands: {e}")
        return []

    def _fix_truncated_json(self, json_str: str) -> Optional[str]:
        in_string = False
        escaped = False
        last_valid_pos = -1
        for i, char in enumerate(json_str):
            if char == '"' and not escaped:
                in_string = not in_string
                if not in_string:
                    last_valid_pos = i
            elif char == '\\' and not escaped:
                escaped = True
                continue
            escaped = False
        if last_valid_pos > 0:
            fixed = json_str[:last_valid_pos + 1] + "]"
            try:
                json.loads(fixed)
                return fixed
            except json.JSONDecodeError:
                pass
        return None

    async def execute_commands(self, commands: list) -> list:
        """Execute a list of commands via RCON."""
        results = []
        for cmd in commands:
            logger.info(f"Executing: {cmd}")
            result = await self.send_command(cmd)
            results.append({"command": cmd, "result": result})
            await asyncio.sleep(0.1)
        return results

    def record_undo(self, player: str, commands: list):
        """Store executed commands for later undo."""
        if player not in UNDO_HISTORY:
            UNDO_HISTORY[player] = []
        UNDO_HISTORY[player].append(list(commands))
        if len(UNDO_HISTORY[player]) > MAX_UNDO_ENTRIES:
            UNDO_HISTORY[player] = UNDO_HISTORY[player][-MAX_UNDO_ENTRIES:]

    def get_log_position(self) -> int:
        try:
            return LOG_FILE.stat().st_size
        except Exception:
            return 0

    def read_new_log_lines(self) -> list:
        lines = []
        try:
            current_size = LOG_FILE.stat().st_size
            if current_size < self.last_log_position:
                self.last_log_position = 0
            if current_size > self.last_log_position:
                with open(LOG_FILE, "r") as f:
                    f.seek(self.last_log_position)
                    lines = f.readlines()
                self.last_log_position = current_size
        except Exception as e:
            logger.error(f"Failed to read log: {e}")
        return lines

    def extract_build_commands(self, line: str) -> Optional[str]:
        """Extract !build or !undo command from log line."""
        patterns = [
            r'<\w+>\s+(!build\s+.+|!undo)',
            r'\w+:\s+(!build\s+.+|!undo)',
            r'(!build\s+.+|!undo)',
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1).strip()
        return None

    async def handle_undo(self, player: str):
        """Revert the last build for the given player."""
        history = UNDO_HISTORY.get(player)
        if not history:
            await self.send_command(
                f"/tellraw {player} {{\"text\":\"Nothing to undo.\",\"color\":\"red\"}}"
            )
            return

        last_commands = history.pop()
        logger.info(f"Undoing {len(last_commands)} commands for {player}")

        # Invert each command: replace block types with air for /fill
        undo_commands = []
        for cmd in last_commands:
            # Simple heuristic: turn /fill ... <block> into /fill ... minecraft:air
            inverted = re.sub(
                r'(minecraft:\w+(?:\s+\d+)?)(?:\s+(replace|keep|outline|hollow|destroy))?$',
                'minecraft:air',
                cmd
            )
            undo_commands.append(inverted)

        results = await self.execute_commands(undo_commands)
        success = sum(1 for r in results if not r["result"].startswith("ERROR"))
        await self.send_command(
            f"/tellraw {player} {{\"text\":\"Undo complete: {success}/{len(undo_commands)} commands reverted.\",\"color\":\"gold\"}}"
        )

    async def process_build_request(self, player: str, request: str):
        """Process a !build or !undo request from a player."""
        request = request.strip()

        # --- !undo ---
        if request == "!undo":
            await self.handle_undo(player)
            return

        # --- !build preset:NAME ---
        preset_match = re.match(r'!build\s+preset:(\w+)', request, re.IGNORECASE)
        if preset_match:
            preset_name = preset_match.group(1).lower()
            if preset_name not in PRESETS:
                await self.send_command(
                    f"/tellraw {player} {{\"text\":\"Unknown preset '{preset_name}'. Available: {', '.join(PRESETS.keys())}\",\"color\":\"red\"}}"
                )
                return
            commands = PRESETS[preset_name]
            logger.info(f"Preset build '{preset_name}' requested by {player}: {len(commands)} commands")
            await self.send_command(
                f"/tellraw {player} {{\"text\":\"Building preset: {preset_name} ({len(commands)} commands)...\",\"color\":\"green\"}}"
            )
            results = await self.execute_commands(commands)
            self.record_undo(player, commands)
            success = sum(1 for r in results if not r["result"].startswith("ERROR"))
            await self.send_command(
                f"/tellraw {player} {{\"text\":\"Preset '{preset_name}' done! {success}/{len(commands)} commands succeeded.\",\"color\":\"gold\"}}"
            )
            return

        # --- !build <free-text prompt> ---
        logger.info(f"Build request from {player}: {request}")
        response = await self.query_ollama(f"Player {player} requests: {request}")

        if response.startswith("ERROR"):
            await self.send_command(f"/tellraw {player} {{\"text\":\"AI Error: {response}\",\"color\":\"red\"}}")
            return

        commands = self.parse_commands(response)
        if not commands:
            await self.send_command(f"/tellraw {player} {{\"text\":\"AI returned no valid commands\",\"color\":\"red\"}}")
            logger.warning(f"No valid commands in response: {response[:200]}")
            return

        await self.send_command(f"/tellraw {player} {{\"text\":\"Building {len(commands)} commands...\",\"color\":\"green\"}}")
        results = await self.execute_commands(commands)
        self.record_undo(player, commands)
        success = sum(1 for r in results if not r["result"].startswith("ERROR"))
        await self.send_command(f"/tellraw {player} {{\"text\":\"Done! {success}/{len(commands)} commands succeeded.\",\"color\":\"gold\"}}")

    async def run(self):
        self.running = True
        logger.info("Starting Minecraft AI Builder...")
        self.last_log_position = self.get_log_position()

        if not await self.connect_rcon():
            logger.error("Initial RCON connection failed, will retry in loop")

        while self.running:
            try:
                if not self.rcon:
                    await self.connect_rcon()
                lines = self.read_new_log_lines()
                for line in lines:
                    build_request = self.extract_build_commands(line)
                    if build_request:
                        player_match = re.search(r'<(\w+)>', line)
                        player = player_match.group(1) if player_match else "Unknown"
                        await self.process_build_request(player, build_request)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(POLL_INTERVAL)

    async def shutdown(self):
        self.running = False
        self.disconnect_rcon()
        await self.http_client.aclose()
        logger.info("Minecraft AI Builder stopped")


async def main():
    builder = MinecraftAIBuilder()
    try:
        await builder.run()
    except KeyboardInterrupt:
        await builder.shutdown()


if __name__ == "__main__":
    asyncio.run(main())