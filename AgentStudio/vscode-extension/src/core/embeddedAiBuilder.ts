import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'yaml';
import { YamlAssistant, ValidationError } from './yamlAssistant';

export interface AgentBlueprint {
    id: string;
    name: string;
    category: string;
    description: string;
    icon: string;
    yamlManifest: string;
    systemPrompt: string;
}

export interface OwnedAgent {
    id: string;
    slug: string;
    name: string;
    description: string;
    category: string;
    version: string;
    trustScore: number;
    status: 'verified' | 'published' | 'draft';
    runsCount: number;
    yamlManifest: string;
    systemPrompt: string;
}

export interface GeneratedAgentResult {
    manifestYaml: string;
    systemPrompt: string;
    validationErrors: ValidationError[];
}

export class EmbeddedAiBuilder {
    public static getOwnedAgents(): OwnedAgent[] {
        return [
            {
                id: 'sec-sentinel-01',
                slug: 'nuuvixx/security-sentinel',
                name: 'Security Sentinel',
                description: 'Autonomous DevSecOps agent for static vulnerability auditing, secret scanning, and automated PII redaction.',
                category: 'Security & DevSecOps',
                version: '1.0.0',
                trustScore: 98.5,
                status: 'verified',
                runsCount: 1420,
                yamlManifest: yaml.stringify({
                    name: 'security-sentinel',
                    slug: 'nuuvixx/security-sentinel',
                    version: '1.0.0',
                    framework: 'AgentOS',
                    description: 'Autonomous DevSecOps agent that performs static vulnerability auditing, secret scanning, and automated PII redaction.',
                    model: {
                        name: 'gpt-4o',
                        temperature: 0.1
                    },
                    tools: [
                        { name: 'secret_scanner', type: 'mcp' },
                        { name: 'pii_redactor', type: 'mcp' },
                        { name: 'cve_analyzer', type: 'mcp' }
                    ],
                    budget: {
                        max_cost_per_run: 0.10,
                        daily_limit: 25.00
                    },
                    policies: {
                        sandbox: { profile: 'strict' },
                        block_unpinned_models: true
                    }
                }),
                systemPrompt: '# Security Sentinel\\n\\nAnalyze codebases for vulnerabilities, hardcoded secrets, and PII leaks.\\n'
            },
            {
                id: 'finops-opt-02',
                slug: 'nuuvixx/finops-cost-optimizer',
                name: 'FinOps Cost Optimizer',
                description: 'Autonomous cloud cost management agent that inspects Kubernetes telemetry and calculates scale-to-zero savings.',
                category: 'Finance & Cloud Infra',
                version: '1.0.0',
                trustScore: 96.0,
                status: 'verified',
                runsCount: 890,
                yamlManifest: yaml.stringify({
                    name: 'finops-cost-optimizer',
                    slug: 'nuuvixx/finops-cost-optimizer',
                    version: '1.0.0',
                    framework: 'AgentOS',
                    description: 'Autonomous cloud cost management agent for Kubernetes workload telemetry.',
                    model: {
                        name: 'claude-3-5-sonnet',
                        temperature: 0.2
                    },
                    tools: [
                        { name: 'k8s_telemetry_collector', type: 'mcp' },
                        { name: 'scale_to_zero_planner', type: 'mcp' }
                    ],
                    budget: {
                        max_cost_per_run: 0.12,
                        daily_limit: 30.00
                    }
                }),
                systemPrompt: '# FinOps Cost Optimizer\\n\\nMonitor cluster resource utilization and recommend automated scale-to-zero policies.\\n'
            },
            {
                id: 'support-agt-03',
                slug: 'nuuvixx/support-agent',
                name: 'Enterprise Support Agent',
                description: 'Autonomous L1 support bot with Zendesk integration and knowledge base search.',
                category: 'Support & Ops',
                version: '1.0.0',
                trustScore: 92.0,
                status: 'published',
                runsCount: 310,
                yamlManifest: yaml.stringify({
                    name: 'support-agent',
                    slug: 'nuuvixx/support-agent',
                    version: '1.0.0',
                    framework: 'AgentOS',
                    description: 'Enterprise support agent with Zendesk integration.',
                    model: {
                        name: 'gpt-4o-mini',
                        temperature: 0.3
                    },
                    tools: [
                        { name: 'get_ticket', type: 'mcp' },
                        { name: 'kb_search', type: 'mcp' }
                    ],
                    budget: {
                        max_cost_per_run: 0.05,
                        daily_limit: 15.00
                    }
                }),
                systemPrompt: '# Enterprise Support Agent\\n\\nResolve customer queries using the knowledge base and escalate tickets when necessary.\\n'
            }
        ];
    }

    public static getBlueprints(): AgentBlueprint[] {
        return [
            {
                id: 'customer-support',
                name: 'Customer Support Specialist',
                category: 'Support & Ops',
                description: 'Autonomous L1 support bot with Zendesk tool access and KB search.',
                icon: 'headset',
                yamlManifest: yaml.stringify({
                    name: 'CustomerSupportAgent',
                    version: '1.0.0',
                    framework: 'AgentOS',
                    description: 'Autonomous L1 Support Bot with Zendesk & KB tools',
                    tools: [
                        { name: 'search_knowledge_base', mcp_server: 'mcp-kb-service' },
                        { name: 'create_zendesk_ticket', mcp_server: 'mcp-zendesk' }
                    ],
                    budget: {
                        max_cost_per_run: 0.15,
                        daily_limit: 10.00
                    },
                    policies: {
                        min_eval_pass_rate: 90,
                        require_human_approval_above_usd: 1.00
                    }
                }),
                systemPrompt: `# Customer Support Specialist\n\nYou are a polite, accurate customer support agent.\n- Rule 1: Always check local Knowledge Base before escalating.\n- Rule 2: Create a Zendesk ticket if resolution fails.\n`
            },
            {
                id: 'fraud-sentinel',
                name: 'Financial Fraud Sentinel',
                category: 'Fintech & Risk',
                description: 'Real-time transaction anomaly detector with risk scoring and ledger audit.',
                icon: 'shield',
                yamlManifest: yaml.stringify({
                    name: 'FraudSentinelAgent',
                    version: '2.1.0',
                    framework: 'AgentOS',
                    description: 'Real-time transaction anomaly detector',
                    tools: [
                        { name: 'fetch_ledger_balance', mcp_server: 'mcp-core-ledger' },
                        { name: 'flag_suspicious_account', mcp_server: 'mcp-risk-api' }
                    ],
                    budget: {
                        max_cost_per_run: 0.25,
                        daily_limit: 50.00
                    },
                    policies: {
                        min_eval_pass_rate: 95,
                        require_ciso_approval: true
                    }
                }),
                systemPrompt: `# Financial Fraud Sentinel\n\nYou monitor real-time transactions for anomalies.\n- Rule 1: Evaluate risk score for transactions > $5,000.\n- Rule 2: Flag accounts automatically if anomaly score > 0.85.\n`
            },
            {
                id: 'devops-leader',
                name: 'DevOps Swarm Leader',
                category: 'Infrastructure',
                description: 'Orchestrates CI/CD deployment pipelines, health checks, and rollback triggers.',
                icon: 'rocket',
                yamlManifest: yaml.stringify({
                    name: 'DevOpsSwarmLeader',
                    version: '1.2.0',
                    framework: 'AgentOS',
                    description: 'Deployment pipeline orchestrator and health checker',
                    tools: [
                        { name: 'query_k8s_cluster', mcp_server: 'mcp-k8s' },
                        { name: 'trigger_github_workflow', mcp_server: 'mcp-github' }
                    ],
                    budget: {
                        max_cost_per_run: 0.20,
                        daily_limit: 25.00
                    },
                    policies: {
                        min_eval_pass_rate: 92,
                        require_team_lead_approval: true
                    }
                }),
                systemPrompt: `# DevOps Swarm Leader\n\nYou manage deployment automation and cluster health checks.\n- Rule 1: Always verify staging metrics before production deployment.\n- Rule 2: Trigger automatic rollback if error rate spikes > 2%.\n`
            },
            {
                id: 'security-auditor',
                name: 'Red-Team Security Auditor',
                category: 'Security & QA',
                description: 'Adversarial prompt injection tester and OWASP compliance scanner.',
                icon: 'search',
                yamlManifest: yaml.stringify({
                    name: 'RedTeamAuditorAgent',
                    version: '1.0.0',
                    framework: 'AgentOS',
                    description: 'Adversarial security fuzzer and compliance scanner',
                    tools: [
                        { name: 'run_owasp_benchmark', mcp_server: 'mcp-security' },
                        { name: 'export_siem_audit', mcp_server: 'mcp-splunk' }
                    ],
                    budget: {
                        max_cost_per_run: 0.30,
                        daily_limit: 30.00
                    },
                    policies: {
                        min_eval_pass_rate: 98,
                        require_ciso_approval: true
                    }
                }),
                systemPrompt: `# Red-Team Security Auditor\n\nYou perform automated security audits and threat modeling.\n- Rule 1: Test against OWASP Top 10 for LLMs.\n- Rule 2: Log all vulnerabilities directly to SIEM audit log.\n`
            }
        ];
    }

    public static generateFromPrompt(promptText: string): GeneratedAgentResult {
        const cleanPrompt = promptText.trim();
        const words = cleanPrompt.split(/\s+/);
        
        // Extract agent name or synthesize from input
        let agentName = 'CustomAgent';
        if (cleanPrompt.toLowerCase().includes('code review') || cleanPrompt.toLowerCase().includes('reviewer')) {
            agentName = 'CodeReviewerAgent';
        } else if (cleanPrompt.toLowerCase().includes('data') || cleanPrompt.toLowerCase().includes('analytics')) {
            agentName = 'DataAnalyticsAgent';
        } else if (words.length >= 2) {
            agentName = words.slice(0, 2).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('') + 'Agent';
            agentName = agentName.replace(/[^a-zA-Z0-9]/g, '');
        }

        // Infer budget cost cap if mentioned in prompt
        let costCap = 0.20;
        const costMatch = cleanPrompt.match(/\$(\d+(?:\.\d+)?)/);
        if (costMatch) {
            costCap = parseFloat(costMatch[1]);
        }

        const manifestObj = {
            name: agentName,
            version: '1.0.0',
            framework: 'AgentOS',
            description: cleanPrompt,
            budget: {
                max_cost_per_run: costCap,
                daily_limit: Math.round(costCap * 100) / 10
            },
            policies: {
                min_eval_pass_rate: 90,
                require_ciso_approval: costCap > 0.5
            }
        };

        const manifestYaml = yaml.stringify(manifestObj);
        const systemPrompt = `# ${agentName}\n\n${cleanPrompt}\n\n## Guidelines\n- Rule 1: Operate strictly within configured token budget ($${costCap.toFixed(2)}).\n- Rule 2: Log key execution steps and tool responses.\n`;

        const validationErrors = YamlAssistant.validateManifest(manifestYaml);

        return {
            manifestYaml,
            systemPrompt,
            validationErrors
        };
    }

    public static async saveAgentFiles(manifestYaml: string, systemPrompt: string, customPath?: string): Promise<string> {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!workspaceFolder) {
            throw new Error('No workspace folder open');
        }

        const targetDir = customPath ? path.join(workspaceFolder, customPath) : workspaceFolder;
        
        if (!fs.existsSync(targetDir)) {
            fs.mkdirSync(targetDir, { recursive: true });
        }

        const manifestPath = path.join(targetDir, 'agent.yaml');
        const promptsDir = path.join(targetDir, 'prompts');
        const systemPromptPath = path.join(promptsDir, 'system.md');

        fs.writeFileSync(manifestPath, manifestYaml, 'utf8');

        if (!fs.existsSync(promptsDir)) {
            fs.mkdirSync(promptsDir, { recursive: true });
        }
        fs.writeFileSync(systemPromptPath, systemPrompt, 'utf8');

        return manifestPath;
    }
}
