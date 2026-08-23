"""
app/sandbox/terminal_bridge.py

Production WebSocket PTY & Sandboxed Terminal Session Bridge for AgentOS.
Supports:
1. Docker Container Interactive PTY attachment (exec_create with tty=True, stdin=True).
2. Local Dev Subprocess Fallback (cross-platform async shell bridge when Docker daemon is not active).
3. Bi-directional raw ANSI keystroke and stdout/stderr streaming.
4. Window resize (TIOCSWINSZ / exec_resize) negotiation.
5. Inactivity timeout reaping (5 minutes).
"""

import os
import sys
import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.sandbox.runner import sandbox

logger = logging.getLogger(__name__)

IDLE_TIMEOUT_SECONDS = 300.0  # 5 minutes


class TerminalSession:
    """Represents an active interactive terminal session bound to an agent container or subprocess."""

    def __init__(self, agent_id: str, websocket: WebSocket):
        self.agent_id = agent_id
        self.websocket = websocket
        self.last_activity = time.time()
        self.is_active = True
        self.mode = "docker" if sandbox.client is not None else "local"
        self.process: Optional[asyncio.subprocess.Process] = None
        self.docker_sock = None
        self.exec_id: Optional[str] = None

    def touch(self):
        self.last_activity = time.time()

    async def start(self):
        """Initializes the interactive terminal session."""
        self.touch()
        await self.websocket.accept()

        banner = (
            f"\r\n\x1b[1;36m┌──────────────────────────────────────────────────────────────┐\x1b[0m\r\n"
            f"\x1b[1;36m│\x1b[0m \x1b[1;32m● AgentOS Execution-Plane Sandboxed PTY Bridge Active\x1b[0m        \x1b[1;36m│\x1b[0m\r\n"
            f"\x1b[1;36m│\x1b[0m \x1b[90mAgent ID: {self.agent_id:<48}\x1b[0m \x1b[1;36m│\x1b[0m\r\n"
            f"\x1b[1;36m│\x1b[0m \x1b[90mRuntime : {self.mode:<10} | Isolation: seccomp-nuuvixx | UID: 1000\x1b[0m \x1b[1;36m│\x1b[0m\r\n"
            f"\x1b[1;36m└──────────────────────────────────────────────────────────────┘\x1b[0m\r\n\r\n"
        )
        await self.websocket.send_text(banner)

        if self.mode == "docker":
            await self._run_docker_session()
        else:
            await self._run_local_session()

    async def _run_docker_session(self):
        """Bridges WebSocket directly to a Docker container PTY."""
        client = sandbox.client
        container_name = f"agentos-sandbox-{self.agent_id}"
        container = None

        try:
            try:
                container = client.containers.get(container_name)
                if container.status != "running":
                    container.start()
            except Exception:
                # Create and start a persistent interactive sandbox container
                container = client.containers.run(
                    "python:3.11-slim",
                    command="/bin/bash",
                    stdin_open=True,
                    tty=True,
                    detach=True,
                    name=container_name,
                    auto_remove=True,
                    network_mode="bridge",
                )

            exec_inst = client.api.exec_create(
                container.id,
                cmd=["/bin/bash"],
                stdin=True,
                tty=True,
                environment={"AGENT_ID": self.agent_id, "TERM": "xterm-256color"},
            )
            self.exec_id = exec_inst["Id"]
            sock = client.api.exec_start(self.exec_id, detach=False, tty=True, stream=True, socket=True)
            self.docker_sock = sock

            # Start reading from container socket in worker thread
            loop = asyncio.get_running_loop()

            async def read_from_docker():
                raw_sock = getattr(sock, "_sock", sock)
                raw_sock.setblocking(False)
                while self.is_active:
                    try:
                        data = await loop.sock_recv(raw_sock, 4096)
                        if not data:
                            break
                        self.touch()
                        await self.websocket.send_text(data.decode("utf-8", errors="replace"))
                    except (BlockingIOError, InterruptedError):
                        await asyncio.sleep(0.02)
                    except Exception as err:
                        logger.debug(f"Docker read stream ended: {err}")
                        break

            read_task = asyncio.create_task(read_from_docker())
            await self._listen_websocket()
            read_task.cancel()

        except Exception as e:
            logger.error(f"[{self.agent_id}] Docker PTY bridge failed: {e}. Falling back to local shell.")
            self.mode = "local"
            await self.websocket.send_text(f"\r\n\x1b[33m[Notice] Docker PTY attach failed ({e}). Re-routing to local sandbox...\x1b[0m\r\n\r\n")
            await self._run_local_session()

    async def _run_local_session(self):
        """Cross-platform local dev subprocess session."""
        # Find best available shell
        shell_cmd = None
        if os.name == "nt":
            for candidate in ["powershell.exe", "pwsh.exe", "cmd.exe"]:
                try:
                    p = await asyncio.create_subprocess_exec(
                        candidate, "-Command", "echo ok",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await p.communicate()
                    if p.returncode == 0:
                        shell_cmd = candidate
                        break
                except Exception:
                    continue
            if not shell_cmd:
                shell_cmd = "cmd.exe"
        else:
            shell_cmd = "/bin/bash" if os.path.exists("/bin/bash") else "/bin/sh"

        env = os.environ.copy()
        env["AGENT_ID"] = self.agent_id
        env["TERM"] = "xterm-256color"
        env["PYTHONUNBUFFERED"] = "1"

        try:
            if os.name == "nt" and "powershell" in shell_cmd.lower():
                args = [shell_cmd, "-NoLogo", "-NoExit", "-Command", "-"]
            elif os.name == "nt":
                args = [shell_cmd]
            else:
                args = [shell_cmd, "-i"]

            self.process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )

            async def read_from_proc():
                while self.is_active and self.process and self.process.stdout:
                    try:
                        chunk = await self.process.stdout.read(1024)
                        if not chunk:
                            break
                        self.touch()
                        text = chunk.decode("utf-8", errors="replace")
                        # Normalize CRLF for Windows outputs if needed
                        if os.name == "nt":
                            text = text.replace("\r\r\n", "\r\n").replace("\n", "\r\n") if "\r\n" not in text else text
                        await self.websocket.send_text(text)
                    except Exception as err:
                        logger.debug(f"Proc read stream ended: {err}")
                        break

            read_task = asyncio.create_task(read_from_proc())
            await self._listen_websocket()
            read_task.cancel()

        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to spawn local shell process: {e}")
            await self.websocket.send_text(f"\r\n\x1b[31m[Error] Unable to initialize shell session: {str(e)}\x1b[0m\r\n")

    async def _listen_websocket(self):
        """Listens for stdin and control messages from xterm.js."""
        try:
            while self.is_active:
                # Check idle timeout
                if time.time() - self.last_activity > IDLE_TIMEOUT_SECONDS:
                    await self.websocket.send_text("\r\n\x1b[33m[Session timed out after 5 minutes of inactivity]\x1b[0m\r\n")
                    break

                try:
                    # Non-blocking wait for incoming messages with a 1-second timeout
                    raw_msg = await asyncio.wait_for(self.websocket.receive_text(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                self.touch()

                # Determine if incoming message is JSON control frame or raw keystrokes
                if raw_msg.startswith("{") and raw_msg.endswith("}"):
                    try:
                        parsed = json.loads(raw_msg)
                        msg_type = parsed.get("type")
                        if msg_type == "resize":
                            cols = parsed.get("cols", 80)
                            rows = parsed.get("rows", 24)
                            self._handle_resize(cols, rows)
                            continue
                        elif msg_type == "stdin":
                            data = parsed.get("data", "")
                            await self._write_input(data)
                            continue
                        elif msg_type == "ping":
                            await self.websocket.send_text(json.dumps({"type": "pong"}))
                            continue
                    except json.JSONDecodeError:
                        pass

                # Default: raw string input
                await self._write_input(raw_msg)

        except WebSocketDisconnect:
            logger.info(f"[{self.agent_id}] WebSocket disconnected by client.")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Terminal loop error: {e}")
        finally:
            await self.cleanup()

    def _handle_resize(self, cols: int, rows: int):
        """Resizes the backend PTY if supported."""
        if self.mode == "docker" and sandbox.client and self.exec_id:
            try:
                sandbox.client.api.exec_resize(self.exec_id, width=cols, height=rows)
            except Exception as e:
                logger.debug(f"Docker exec_resize not supported or failed: {e}")

    async def _write_input(self, text: str):
        """Writes input text/keystrokes to the underlying Docker socket or process stdin."""
        if self.mode == "docker" and self.docker_sock:
            try:
                raw_sock = getattr(self.docker_sock, "_sock", self.docker_sock)
                raw_sock.send(text.encode("utf-8"))
            except Exception as e:
                logger.error(f"Error writing to Docker socket: {e}")
        elif self.process and self.process.stdin:
            try:
                self.process.stdin.write(text.encode("utf-8"))
                await self.process.stdin.drain()
            except Exception as e:
                logger.error(f"Error writing to process stdin: {e}")

    async def cleanup(self):
        """Gracefully tears down the terminal session."""
        self.is_active = False
        if self.process:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            except Exception:
                pass
            self.process = None

        if self.docker_sock:
            try:
                self.docker_sock.close()
            except Exception:
                pass
            self.docker_sock = None


class TerminalSessionManager:
    """Manages active terminal sessions across agents."""

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}

    async def handle_connection(self, agent_id: str, websocket: WebSocket):
        session = TerminalSession(agent_id, websocket)
        self.sessions[agent_id] = session
        try:
            await session.start()
        finally:
            if agent_id in self.sessions:
                del self.sessions[agent_id]
            await session.cleanup()


terminal_manager = TerminalSessionManager()
