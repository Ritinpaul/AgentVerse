import click
import os
import subprocess
import yaml
import json
import httpx
import sys

def get_agent_yaml():
    if not os.path.exists("agent.yaml"):
        click.secho("Error: agent.yaml not found in current directory.", fg="red")
        sys.exit(1)
    with open("agent.yaml", "r") as f:
        return yaml.safe_load(f)

@click.group()
def cli():
    """Nuuvixx CLI - Manage and deploy AgentOS autonomous agents."""
    pass

@cli.command()
def dev():
    """Start the local AgentOS/GovernOS runtime for local testing."""
    click.secho("Starting local Nuuvixx runtime...", fg="blue")
    
    # We will assume AgentOS repository is cloned and accessible or 
    # we have a centralized docker-compose file for the local-runtime.
    # For this prototype, we'll run a local compose if found.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    compose_file = os.path.abspath(os.path.join(script_dir, "../../../infra/docker-compose.yml"))
    
    if os.path.exists(compose_file):
        subprocess.run(["docker-compose", "-f", compose_file, "up", "-d"])
        click.secho("Local runtime started successfully.", fg="green")
    else:
        click.secho(f"Local runtime compose file not found at {compose_file}. Using global installation or existing running containers.", fg="yellow")

@cli.command()
def run():
    """Run the agent defined in agent.yaml locally."""
    config = get_agent_yaml()
    agent_name = config.get("name", "unknown")
    click.secho(f"Running agent '{agent_name}' locally...", fg="blue")
    
    # 1. Send to local AgentGovern OS for policy check
    govern_url = os.getenv("AGENTGOVERN_URL", "http://localhost:8001")
    click.secho("Checking policies with AgentGovern OS...", fg="cyan")
    try:
        resp = httpx.post(f"{govern_url}/governance/evaluate", json=config, timeout=5.0)
        result = resp.json()
        if not result.get("allowed", True):
            click.secho("Governance Check Failed:", fg="red", bold=True)
            for v in result.get("violations", []):
                click.secho(f" - {v}", fg="red")
            sys.exit(1)
        else:
            click.secho("Governance Check Passed.", fg="green")
    except Exception as e:
        click.secho(f"Warning: Could not reach local AgentGovern OS ({e}). Proceeding without policy check.", fg="yellow")

    # 2. Spawn on local AgentOS Control Plane
    control_url = os.getenv("AGENTOS_CONTROL_URL", "http://localhost:8010")
    click.secho(f"Deploying to local execution plane...", fg="cyan")
    
    payload = {
        "name": agent_name,
        "instructions": config.get("description", ""),
        "config": config
    }
    
    try:
        resp = httpx.post(f"{control_url}/lifecycle/boot", json=payload, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        click.secho(f"Agent booted successfully! Agent ID: {data.get('agent_id')}", fg="green", bold=True)
    except Exception as e:
        click.secho(f"Failed to boot agent on local AgentOS: {e}", fg="red")

@cli.command()
def deploy():
    """Deploy the agent to the production AgentOS cloud."""
    config = get_agent_yaml()
    agent_name = config.get("name", "unknown")
    click.secho(f"Deploying agent '{agent_name}' to Nuuvixx Cloud...", fg="blue", bold=True)
    click.secho("Not implemented for Phase 1. Use 'nuuvixx run' for local deployment.", fg="yellow")

if __name__ == "__main__":
    cli()
