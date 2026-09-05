/**
 * GitHub-Standard & AWS IAM Architecture Permission Matrix
 * 
 * GitHub Roles (Legacy Compatibility):
 * 1. owner  - Full Org & Billing Ownership (Billing, Org Delete, Ownership Transfer)
 * 2. admin  - Repo & Infrastructure Admin (Manage MicroVMs, Policies, Team Members, Keys)
 * 3. write  - Developer (Edit agent.yaml, push code, deploy staging)
 * 4. triage - Operator (Run agents, approve GovernOS policy gates)
 * 5. read   - Viewer/Auditor (Read-only access to traces and audit ledgers)
 * 
 * AWS IAM Architecture Additions:
 * - ARN Specification: arn:agentverse:<pillar>:<region>:<org_id>:<resource_type>/<resource_id>
 * - IAM Assumed Role Sessions (Short-lived STS Token Sessions)
 */

export type GitHubRole = "owner" | "admin" | "write" | "triage" | "read" | "developer" | "viewer" | "operator";

export interface GitHubRolePermissions {
  roleLabel: string;
  badgeColor: string;
  canManageBilling: boolean;
  canDeleteOrg: boolean;
  canTransferOwnership: boolean;
  canRotateMasterKeys: boolean;
  canManageTeam: boolean;
  canEditPolicies: boolean;
  canDeployMicroVMs: boolean;
  canApproveGates: boolean;
  canViewAuditLogs: boolean;
}

export interface IAMRoleDefinition {
  roleArn: string;
  name: string;
  description: string;
  badgeColor: string;
  legacyRole: GitHubRole;
}

export interface AssumedRoleSession {
  assumedRoleArn: string;
  roleName: string;
  sessionToken: string;
  expiresAt: number;
  userArn: string;
  badgeColor: string;
  permissions: string[];
}

export const PRESET_IAM_ROLES: IAMRoleDefinition[] = [
  {
    roleArn: "arn:agentverse:iam::org_default:role/OwnerRole",
    name: "Organization Owner",
    description: "Full Root Super-Admin access to Billing, Org Deletion, Key Rotation, & Policies",
    badgeColor: "bg-[#EC4899]/15 border-[#EC4899]/40 text-[#F472B6]",
    legacyRole: "owner",
  },
  {
    roleArn: "arn:agentverse:iam::org_default:role/AdminRole",
    name: "System Administrator",
    description: "Manage Team Members, MicroVM Infrastructure, and GovernOS Safety Policies",
    badgeColor: "bg-[#8B5CF6]/15 border-[#8B5CF6]/40 text-[#C084FC]",
    legacyRole: "admin",
  },
  {
    roleArn: "arn:agentverse:iam::org_default:role/DeveloperRole",
    name: "Agent Developer (Write)",
    description: "Develop agents, edit prompts, test locally, and deploy to Staging MicroVMs",
    badgeColor: "bg-[#10B981]/15 border-[#10B981]/40 text-[#34D399]",
    legacyRole: "write",
  },
  {
    roleArn: "arn:agentverse:iam::org_default:role/AuditorRole",
    name: "Compliance Auditor (Read)",
    description: "Read-only access to audit ledgers, telemetry traces, and compliance reports",
    badgeColor: "bg-[#3B82F6]/15 border-[#3B82F6]/30 text-[#60A5FA]",
    legacyRole: "read",
  },
];

export function getGitHubRolePermissions(roleStr?: string): GitHubRolePermissions {
  const normalized = (roleStr || "read").toLowerCase() as GitHubRole;

  const isOwner = normalized === "owner";
  const isAdmin = isOwner || normalized === "admin";
  const isWrite = isAdmin || normalized === "write" || normalized === "developer";
  const isTriage = isWrite || normalized === "triage" || normalized === "operator";
  const isRead = true;

  let roleLabel = "Viewer (Read)";
  let badgeColor = "bg-[#3B82F6]/15 border-[#3B82F6]/30 text-[#60A5FA]";

  if (isOwner) {
    roleLabel = "Organization Owner";
    badgeColor = "bg-[#EC4899]/15 border-[#EC4899]/40 text-[#F472B6]";
  } else if (normalized === "admin") {
    roleLabel = "System Admin";
    badgeColor = "bg-[#8B5CF6]/15 border-[#8B5CF6]/40 text-[#C084FC]";
  } else if (normalized === "write" || normalized === "developer") {
    roleLabel = "Member (Write)";
    badgeColor = "bg-[#10B981]/15 border-[#10B981]/40 text-[#34D399]";
  } else if (normalized === "triage" || normalized === "operator") {
    roleLabel = "Operator (Triage)";
    badgeColor = "bg-[#F59E0B]/15 border-[#F59E0B]/40 text-[#FBBF24]";
  }

  return {
    roleLabel,
    badgeColor,
    canManageBilling: isOwner,
    canDeleteOrg: isOwner,
    canTransferOwnership: isOwner,
    canRotateMasterKeys: isOwner,
    canManageTeam: isAdmin,
    canEditPolicies: isAdmin,
    canDeployMicroVMs: isWrite,
    canApproveGates: isTriage,
    canViewAuditLogs: isRead,
  };
}

/** Parse an AgentVerse ARN string */
export function parseARN(arn: string) {
  const match = arn.match(/^arn:agentverse:([a-z0-9_-]+):([a-z0-9_-]*):([a-z0-9_-]+):([a-z0-9_-]+)\/(.+)$/);
  if (!match) return null;
  return {
    pillar: match[1],
    region: match[2],
    orgId: match[3],
    resourceType: match[4],
    resourceId: match[5],
  };
}
