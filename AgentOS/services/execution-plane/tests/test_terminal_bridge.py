import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.sandbox.terminal_bridge import TerminalSessionManager, TerminalSession

client = TestClient(app)

def test_terminal_websocket_connect():
    """Verify xterm WebSocket connects and receives banner."""
    with client.websocket_connect("/ws/terminal/agent-test-pty") as websocket:
        data = websocket.receive_text()
        assert "AgentOS Execution-Plane Sandboxed PTY Bridge Active" in data
        assert "agent-test-pty" in data

        # Send a ping frame
        websocket.send_text('{"type": "ping"}')
        pong = websocket.receive_text()
        assert '"type": "pong"' in pong or "pong" in pong

def test_execute_terminal_websocket_alias():
    """Verify /execute/ws/terminal/{agent_id} router mount works identically."""
    with client.websocket_connect("/execute/ws/terminal/agent-alias-pty") as websocket:
        data = websocket.receive_text()
        assert "AgentOS Execution-Plane Sandboxed PTY Bridge Active" in data
        assert "agent-alias-pty" in data
