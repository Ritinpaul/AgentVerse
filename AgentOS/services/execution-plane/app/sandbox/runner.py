"""
AgentOS Execution Plane - Sandboxed Container Runtime & Isolation Infrastructure
Implements:
1. Docker Container Isolation (read-only rootfs, tmpfs mounts, capability dropping, no-new-privileges)
2. Per-Agent Resource Metering (CPU, Memory, Network I/O, Execution Duration)
3. Checkpoint/Snapshot State Recovery
4. Resilient LLM Fallback Routing (Groq -> Mistral -> Cerebras -> OpenRouter -> Gemini)
5. Scale-to-zero container cleanup logic
"""

import os
import docker
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DEFAULT_SECCOMP_PATH = Path(__file__).resolve().parent.parent.parent / "security" / "seccomp-nuuvixx.json"


class ExecutionMeter:
    """Tracks CPU time, peak memory usage, network I/O, and runtime per agent execution."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.cpu_time_ms: float = 0.0
        self.peak_memory_mb: float = 0.0
        self.network_tx_bytes: int = 0
        self.network_rx_bytes: int = 0

    def record_completion(self, stats: Optional[Dict[str, Any]] = None):
        self.end_time = time.time()
        if stats:
            # Memory stats
            mem_usage = stats.get("memory_stats", {}).get("usage", 0)
            self.peak_memory_mb = round(mem_usage / (1024 * 1024), 2)

            # CPU stats
            cpu_stats = stats.get("cpu_stats", {})
            cpu_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            self.cpu_time_ms = round(cpu_usage / 1_000_000, 2)

            # Network stats
            networks = stats.get("networks", {})
            for net_info in networks.values():
                self.network_rx_bytes += net_info.get("rx_bytes", 0)
                self.network_tx_bytes += net_info.get("tx_bytes", 0)

    def to_dict(self) -> Dict[str, Any]:
        duration = (self.end_time or time.time()) - self.start_time
        return {
            "agent_id": self.agent_id,
            "duration_seconds": round(duration, 3),
            "cpu_time_ms": self.cpu_time_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "network_tx_bytes": self.network_tx_bytes,
            "network_rx_bytes": self.network_rx_bytes,
        }


class FallbackModelRouter:
    """Intelligent fallback routing across LLM providers for high availability."""

    FALLBACK_CHAINS = {
        "groq": ["groq", "mistral", "cerebras", "openrouter", "gemini"],
        "mistral": ["mistral", "groq", "openrouter", "gemini"],
        "cerebras": ["cerebras", "groq", "openrouter"],
        "anthropic": ["anthropic", "openrouter", "groq"],
        "openai": ["openai", "openrouter", "groq"],
    }

    @classmethod
    def get_fallback_chain(cls, primary_provider: str) -> List[str]:
        provider_lower = (primary_provider or "groq").lower()
        return cls.FALLBACK_CHAINS.get(provider_lower, [provider_lower, "groq", "openrouter"])


class DockerSandbox:
    """
    Production-grade container isolation runtime using Docker Micro-Sandbox semantics.
    Supports read-only rootfs, tmpfs mounts, drop-capabilities, resource limits, metering,
    and state snapshots.
    """

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not connect to Docker daemon: {e}. Sandboxes will use mock execution.")
            self.client = None

        self.running_containers: Dict[str, Any] = {}
        self.meters: Dict[str, ExecutionMeter] = {}
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self.last_activity: Dict[str, float] = {}
        self.last_execution_configs: Dict[str, Dict[str, Any]] = {}

    def get_seccomp_profile_path(self) -> Optional[Path]:
        """Resolves the active seccomp JSON security profile."""
        custom_path = os.getenv("AGENTOS_SECCOMP_PROFILE_PATH")
        if custom_path:
            p = Path(custom_path)
            if p.exists():
                return p
        if DEFAULT_SECCOMP_PATH.exists():
            return DEFAULT_SECCOMP_PATH
        return None

    def build_security_opts(self) -> List[str]:
        """Builds Docker security options with no-new-privileges and custom seccomp profile."""
        opts = ["no-new-privileges:true"]
        profile_path = self.get_seccomp_profile_path()
        if profile_path:
            opts.append(f"seccomp={profile_path.resolve().as_posix()}")
        return opts

    def build_tmpfs_mounts(self) -> Dict[str, str]:
        """Configures strict tmpfs filesystem mounts with noexec, nosuid, and nodev isolation."""
        return {
            "/tmp": "rw,noexec,nosuid,nodev,size=64m",
            "/workspace": "rw,nosuid,nodev,size=256m",
            "/run": "rw,noexec,nosuid,nodev,size=16m",
            "/root/.cache": "rw,noexec,nosuid,nodev,size=64m",
        }

    def start_execution(
        self,
        agent_id: str,
        entrypoint: str,
        env_vars: Dict[str, str],
        mem_limit: str = "512m",
        cpu_quota: int = 50000,
        read_only_fs: bool = True,
        pids_limit: Optional[int] = None,
    ):
        logger.info(f"[{agent_id}] Starting isolated sandbox execution: {entrypoint}")

        env = env_vars.copy()
        env["AGENTOS_AGENT_ID"] = agent_id
        env["AGENTOS_SANDBOX_ISOLATED"] = "true"

        if pids_limit is None:
            pids_limit = int(os.getenv("AGENTOS_SANDBOX_PIDS_LIMIT", "100"))

        security_opts = self.build_security_opts()
        tmpfs_mounts = self.build_tmpfs_mounts()

        # Track applied execution configuration for verification & telemetry
        self.last_execution_configs[agent_id] = {
            "entrypoint": entrypoint,
            "mem_limit": mem_limit,
            "cpu_quota": cpu_quota,
            "read_only": read_only_fs,
            "tmpfs": tmpfs_mounts,
            "security_opt": security_opts,
            "pids_limit": pids_limit,
        }

        # Initialize metering
        meter = ExecutionMeter(agent_id)
        self.meters[agent_id] = meter
        self.last_activity[agent_id] = time.time()

        if not self.client:
            logger.warning(f"[{agent_id}] Running in dry-run/mock sandbox mode (no Docker daemon)")
            return

        try:
            # Hardened container parameters
            container = self.client.containers.run(
                "python:3.11-slim",
                command=entrypoint,
                environment=env,
                detach=True,
                name=f"agentos-sandbox-{agent_id}",
                # 1. Memory & CPU Resource Quotas + Fork Bomb Protection
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                cpu_period=100000,
                pids_limit=pids_limit,
                # 2. Filesystem Isolation (Read-only rootfs + tmpfs mounts)
                read_only=read_only_fs,
                tmpfs=tmpfs_mounts,
                # 3. Security Hardening (Seccomp profile + capability dropping)
                cap_drop=["ALL"],
                security_opt=security_opts,
                network_mode="bridge",
                auto_remove=True
            )
            self.running_containers[agent_id] = container
        except Exception as e:
            logger.error(f"[{agent_id}] Failed to launch container sandbox: {e}")
            raise

    def stop_execution(self, agent_id: str) -> bool:
        """Stops execution and records final resource metrics."""
        self.last_activity[agent_id] = time.time()
        
        # Collect final stats if available
        if agent_id in self.running_containers:
            container = self.running_containers[agent_id]
            try:
                if self.client:
                    stats = container.stats(stream=False)
                    if agent_id in self.meters:
                        self.meters[agent_id].record_completion(stats)
                container.stop(timeout=5)
            except Exception as e:
                logger.error(f"[{agent_id}] Error stopping sandbox container: {e}")
            finally:
                del self.running_containers[agent_id]
            return True

        if agent_id in self.meters:
            self.meters[agent_id].record_completion()
            return True

        # Fallback container check
        if self.client:
            try:
                container = self.client.containers.get(f"agentos-sandbox-{agent_id}")
                container.stop(timeout=5)
                return True
            except docker.errors.NotFound:
                pass

        return False

    def get_metering_stats(self, agent_id: str) -> Dict[str, Any]:
        """Returns metering statistics for an agent execution."""
        meter = self.meters.get(agent_id)
        if meter:
            return meter.to_dict()
        return {
            "agent_id": agent_id,
            "duration_seconds": 0.0,
            "cpu_time_ms": 0.0,
            "peak_memory_mb": 0.0,
            "network_tx_bytes": 0,
            "network_rx_bytes": 0,
        }

    def checkpoint_snapshot(self, run_id: str, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves run state checkpoint snapshot for recovery."""
        snapshot = {
            "run_id": run_id,
            "timestamp": time.time(),
            "state_data": state_data,
        }
        self.snapshots[run_id] = snapshot
        logger.info(f"[Checkpoint] Saved snapshot for run {run_id}")
        return snapshot

    def restore_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Restores run state checkpoint snapshot."""
        snapshot = self.snapshots.get(run_id)
        if snapshot:
            logger.info(f"[Checkpoint] Restored snapshot for run {run_id}")
            return snapshot["state_data"]
        return None

    def reap_idle_containers(self, max_idle_seconds: float = 60.0) -> List[str]:
        """Scale-to-zero logic: reaps containers idle for longer than max_idle_seconds."""
        now = time.time()
        reaped = []
        for agent_id, last_time in list(self.last_activity.items()):
            if now - last_time > max_idle_seconds:
                if self.stop_execution(agent_id):
                    reaped.append(agent_id)
                    del self.last_activity[agent_id]
        if reaped:
            logger.info(f"[Scale-to-Zero] Reaped {len(reaped)} idle container sandboxes: {reaped}")
        return reaped


sandbox = DockerSandbox()
