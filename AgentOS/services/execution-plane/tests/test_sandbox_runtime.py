import time
from app.sandbox.runner import DockerSandbox, FallbackModelRouter, ExecutionMeter

def test_fallback_model_router():
    # Primary groq fallback chain
    groq_chain = FallbackModelRouter.get_fallback_chain("groq")
    assert groq_chain[0] == "groq"
    assert "mistral" in groq_chain
    assert "openrouter" in groq_chain

    # Unknown provider default chain
    unknown_chain = FallbackModelRouter.get_fallback_chain("custom_llm")
    assert "groq" in unknown_chain

def test_execution_metering():
    meter = ExecutionMeter("test-agent-01")
    time.sleep(0.01)
    
    mock_stats = {
        "memory_stats": {"usage": 52428800}, # 50 MB
        "cpu_stats": {"cpu_usage": {"total_usage": 150000000}}, # 150 ms
        "networks": {"eth0": {"rx_bytes": 1024, "tx_bytes": 2048}}
    }
    meter.record_completion(mock_stats)
    data = meter.to_dict()

    assert data["agent_id"] == "test-agent-01"
    assert data["duration_seconds"] > 0
    assert data["peak_memory_mb"] == 50.0
    assert data["cpu_time_ms"] == 150.0
    assert data["network_rx_bytes"] == 1024
    assert data["network_tx_bytes"] == 2048

def test_docker_sandbox_mock_execution():
    sandbox = DockerSandbox()
    # Force mock mode by clearing client
    sandbox.client = None

    sandbox.start_execution("sec-agent", "echo 'hello'", {"FOO": "BAR"})
    stats = sandbox.get_metering_stats("sec-agent")
    assert stats["agent_id"] == "sec-agent"

    stopped = sandbox.stop_execution("sec-agent")
    assert stopped is True

def test_checkpoint_and_restore():
    sandbox = DockerSandbox()
    run_id = "run-1002"
    checkpoint_data = {"step": 3, "memory": ["usr: hello", "bot: hi"]}

    saved = sandbox.checkpoint_snapshot(run_id, checkpoint_data)
    assert saved["run_id"] == run_id

    restored = sandbox.restore_checkpoint(run_id)
    assert restored == checkpoint_data
    assert restored["step"] == 3

def test_scale_to_zero_reaper():
    sandbox = DockerSandbox()
    sandbox.client = None

    sandbox.start_execution("idle-agent-1", "python -c 'pass'", {})
    sandbox.last_activity["idle-agent-1"] = time.time() - 100 # 100 seconds ago

    reaped = sandbox.reap_idle_containers(max_idle_seconds=60.0)
    assert "idle-agent-1" in reaped


def test_seccomp_profile_validity():
    import json
    from app.sandbox.runner import DEFAULT_SECCOMP_PATH

    assert DEFAULT_SECCOMP_PATH.exists(), f"Seccomp profile missing at {DEFAULT_SECCOMP_PATH}"
    with open(DEFAULT_SECCOMP_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("defaultAction") == "SCMP_ACT_ALLOW"
    assert "syscalls" in data
    syscalls = data["syscalls"]
    assert len(syscalls) > 0

    blocked = set()
    for entry in syscalls:
        if entry.get("action") == "SCMP_ACT_ERRNO":
            for name in entry.get("names", []):
                blocked.add(name)

    critical_blocked = ["ptrace", "unshare", "kexec_load", "bpf", "reboot", "swapon", "mount", "pivot_root"]
    for sc in critical_blocked:
        assert sc in blocked, f"Syscall {sc} should be explicitly blocked in seccomp profile"


def test_docker_sandbox_hardening_options():
    sandbox = DockerSandbox()
    sec_opts = sandbox.build_security_opts()
    assert "no-new-privileges:true" in sec_opts
    assert any(opt.startswith("seccomp=") for opt in sec_opts)

    tmpfs = sandbox.build_tmpfs_mounts()
    assert "/tmp" in tmpfs
    assert "/workspace" in tmpfs
    assert "/run" in tmpfs
    assert "/root/.cache" in tmpfs
    assert "noexec" in tmpfs["/tmp"]
    assert "nodev" in tmpfs["/tmp"]
    assert "nosuid" in tmpfs["/tmp"]
    assert "nodev" in tmpfs["/workspace"]


def test_docker_sandbox_execution_configuration():
    sandbox = DockerSandbox()
    sandbox.client = None

    sandbox.start_execution("agent-hardening-test", "python -m agent", {"ENV": "prod"})
    cfg = sandbox.last_execution_configs.get("agent-hardening-test")
    assert cfg is not None
    assert cfg["read_only"] is True
    assert cfg["pids_limit"] == 100
    assert "/workspace" in cfg["tmpfs"]
    assert any(opt.startswith("seccomp=") for opt in cfg["security_opt"])

