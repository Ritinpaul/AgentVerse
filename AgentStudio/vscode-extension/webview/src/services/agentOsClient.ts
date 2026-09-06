export interface SwarmState {
    id: string;
    name: string;
    manager_agent_id: string;
    worker_agent_ids: string[];
}

export interface LogMessage {
    agent_id: string;
    timestamp: string;
    content: string;
}

export class AgentOsClient {
    private wsConnections: Map<string, WebSocket> = new Map();
    private listeners: ((msg: LogMessage) => void)[] = [];

    // Assuming AgentOS Control Plane is on port 8010 (from our docker-compose)
    private readonly CONTROL_PLANE_URL = 'http://localhost:8010';
    // State Plane is on 8012
    private readonly STATE_PLANE_WS = 'ws://localhost:8012';

    async fetchLatestSwarm(): Promise<SwarmState | null> {
        try {
            const response = await fetch(`${this.CONTROL_PLANE_URL}/swarms`);
            if (response.ok) {
                const swarms = await response.json();
                if (Array.isArray(swarms) && swarms.length > 0) {
                    // return the most recently created swarm
                    return swarms[swarms.length - 1];
                }
            }
        } catch {
            // AgentOS control plane offline - silent fallback
        }
        return null;
    }

    subscribeToAgent(agentId: string) {
        if (this.wsConnections.has(agentId)) {
            return;
        }

        const ws = new WebSocket(`${this.STATE_PLANE_WS}/messages/stream/${agentId}`);
        
        ws.onopen = () => {
            console.log(`Connected to log stream for agent ${agentId}`);
            this.notify({ agent_id: 'SYSTEM', timestamp: new Date().toISOString(), content: `Connected to stream: ${agentId}` });
        };

        ws.onmessage = (event) => {
            try {
                // Try parsing if it's JSON
                let data = event.data;
                try {
                    const parsed = JSON.parse(event.data);
                    data = parsed.content || JSON.stringify(parsed);
                } catch(e) {}
                
                this.notify({
                    agent_id: agentId,
                    timestamp: new Date().toISOString(),
                    content: data
                });
            } catch (err) {
                console.error(err);
            }
        };

        ws.onerror = (err) => {
            console.error(`WebSocket error for ${agentId}`, err);
        };

        this.wsConnections.set(agentId, ws);
    }

    onMessage(callback: (msg: LogMessage) => void): () => void {
        this.listeners.push(callback);
        return () => {
            this.listeners = this.listeners.filter(cb => cb !== callback);
        };
    }

    private notify(msg: LogMessage) {
        this.listeners.forEach(cb => cb(msg));
    }

    disconnect() {
        this.wsConnections.forEach(ws => ws.close());
        this.wsConnections.clear();
    }
}
