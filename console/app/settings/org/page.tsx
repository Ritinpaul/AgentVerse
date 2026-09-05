"use client";

import React, { useState, useEffect } from "react";
import {
  Building2,
  Users,
  ShieldCheck,
  CreditCard,
  Lock,
  Plus,
  Trash2,
  Check,
  UserPlus,
  X,
  Shield,
  Key,
  ChevronDown
} from "lucide-react";
import { getStoredUser, UserProfile } from "@/lib/auth";
import { getGitHubRolePermissions, GitHubRole } from "@/lib/rbac";

export interface WorkspaceMember {
  id: string;
  name: string;
  email: string;
  role: GitHubRole;
  joinedAt: string;
  isSelf?: boolean;
}

const DEFAULT_MEMBERS: WorkspaceMember[] = [
  {
    id: "m-owner",
    name: "Platform Executive",
    email: "owner@nuuvixx.ai",
    role: "owner",
    joinedAt: "2026-01-15",
    isSelf: true,
  },
  {
    id: "m-admin",
    name: "System Administrator",
    email: "admin@nuuvixx.ai",
    role: "admin",
    joinedAt: "2026-02-01",
  },
  {
    id: "m-dev",
    name: "Agent Developer",
    email: "developer@nuuvixx.ai",
    role: "developer",
    joinedAt: "2026-02-10",
  },
  {
    id: "m-auditor",
    name: "Compliance Auditor",
    email: "auditor@nuuvixx.ai",
    role: "read",
    joinedAt: "2026-02-18",
  },
];

export default function OrgSettingsPage() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isCopied, setIsCopied] = useState(false);
  const [members, setMembers] = useState<WorkspaceMember[]>(DEFAULT_MEMBERS);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);

  // Invite Form State
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<GitHubRole>("developer");
  const [inviteError, setInviteError] = useState<string | null>(null);

  useEffect(() => {
    const storedUser = getStoredUser();
    setUser(storedUser);

    try {
      const saved = localStorage.getItem("agentverse_workspace_members");
      let activeMembers = DEFAULT_MEMBERS;
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          activeMembers = parsed;
        }
      }

      if (storedUser) {
        // Ensure stored user is present in workspace members with isSelf=true
        const existingIdx = activeMembers.findIndex(
          (m) => m.email.toLowerCase() === storedUser.email.toLowerCase()
        );
        if (existingIdx !== -1) {
          activeMembers[existingIdx] = {
            ...activeMembers[existingIdx],
            name: storedUser.name || activeMembers[existingIdx].name,
            role: storedUser.role as GitHubRole,
            isSelf: true,
          };
        } else {
          activeMembers.unshift({
            id: "m-self-" + storedUser.id,
            name: storedUser.name || "Workspace Member",
            email: storedUser.email,
            role: storedUser.role as GitHubRole,
            joinedAt: new Date().toISOString().split("T")[0],
            isSelf: true,
          });
        }
      }
      setMembers(activeMembers);
    } catch (e) {
      console.error("Failed to load workspace members", e);
    }
  }, []);

  const saveMembers = (newMembers: WorkspaceMember[]) => {
    setMembers(newMembers);
    try {
      localStorage.setItem("agentverse_workspace_members", JSON.stringify(newMembers));
    } catch (e) {
      console.error("Failed to persist members", e);
    }
  };

  const copySlug = () => {
    if (user?.org_slug) {
      navigator.clipboard.writeText(user.org_slug);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  const handleAddMember = (e: React.FormEvent) => {
    e.preventDefault();
    setInviteError(null);

    if (!inviteName.trim() || !inviteEmail.trim()) {
      setInviteError("Name and email address are required.");
      return;
    }

    if (members.some((m) => m.email.toLowerCase() === inviteEmail.trim().toLowerCase())) {
      setInviteError("A workspace member with this email address already exists.");
      return;
    }

    const newMember: WorkspaceMember = {
      id: "m-" + Date.now(),
      name: inviteName.trim(),
      email: inviteEmail.trim().toLowerCase(),
      role: inviteRole,
      joinedAt: new Date().toISOString().split("T")[0],
    };

    saveMembers([...members, newMember]);
    setInviteName("");
    setInviteEmail("");
    setInviteRole("developer");
    setIsInviteModalOpen(false);
  };

  const handleRoleChange = (memberId: string, newRole: GitHubRole) => {
    const updated = members.map((m) =>
      m.id === memberId ? { ...m, role: newRole } : m
    );
    saveMembers(updated);
  };

  const handleRemoveMember = (memberId: string) => {
    const updated = members.filter((m) => m.id !== memberId);
    saveMembers(updated);
  };

  if (!user) return null;

  const perms = getGitHubRolePermissions(user.role);

  return (
    <div className="space-y-6 max-w-5xl mx-auto selection:bg-purple-600/30 selection:text-white">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-purple-400" />
            <h1 className="text-xl font-bold font-mono text-white">
              Organization & Workspace Settings
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono font-semibold uppercase">
              {user.org_tier} Tier
            </span>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Manage your workspace details, invite team members, and assign fine-grained AWS IAM / RBAC roles (Owner, Admin, Write, Read).
          </p>
        </div>
      </div>

      {/* Grid Settings Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Org Overview */}
        <div
          className="p-5 rounded-sm space-y-4 col-span-2"
          style={{ background: "#13141f", border: "1px solid rgba(255,255,255,0.07)" }}
        >
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              ORGANIZATION DETAILS
            </span>
            <ShieldCheck className="w-4 h-4 text-purple-400" />
          </div>

          <div className="grid grid-cols-2 gap-4 font-mono text-xs">
            <div>
              <div className="text-neutral-500 text-[11px] mb-1">Organization Name</div>
              <div className="text-white font-bold">{user.org_name || "Nuuvixx AI Systems"}</div>
            </div>
            <div>
              <div className="text-neutral-500 text-[11px] mb-1">Namespace Slug</div>
              <div className="flex items-center gap-2">
                <code className="text-purple-300 bg-purple-950/40 px-2 py-0.5 rounded border border-purple-500/20">
                  {user.org_slug || "nuuvixx-autonomous"}
                </code>
                <button
                  onClick={copySlug}
                  className="text-neutral-400 hover:text-white transition-colors"
                  title="Copy Namespace Slug"
                >
                  {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : "Copy"}
                </button>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-white/5 space-y-2">
            <div className="text-neutral-500 text-[11px] font-mono">Agent Namespace Scope</div>
            <p className="font-mono text-[11px] text-neutral-300">
              All agents built in AgentStudio are published as{" "}
              <span className="text-purple-400">{user.org_slug}/[agent_name]</span> (e.g.{" "}
              <span className="text-purple-300">{user.org_slug}/job-tracker</span>).
            </p>
          </div>
        </div>

        {/* Quota & Billing */}
        <div
          className="p-5 rounded-sm space-y-4"
          style={{ background: "#13141f", border: "1px solid rgba(255,255,255,0.07)" }}
        >
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              QUOTA & BILLING
            </span>
            <CreditCard className="w-4 h-4 text-purple-400" />
          </div>

          {perms.canManageBilling ? (
            <div className="space-y-3 font-mono">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-neutral-400">Monthly Usage</span>
                  <span className="text-white font-bold">$142.50 / $2,500.00</span>
                </div>
                <div className="w-full h-2 bg-black/50 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500 rounded-full" style={{ width: "5.7%" }} />
                </div>
              </div>

              <div className="text-[11px] text-neutral-400 space-y-1">
                <div className="flex justify-between">
                  <span>Active Workspace Members:</span>
                  <span className="text-white font-bold">{members.length}</span>
                </div>
                <div className="flex justify-between">
                  <span>Data Region:</span>
                  <span className="text-white">us-east-1</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-black/40 rounded border border-white/10 space-y-2 text-xs font-mono">
              <div className="flex items-center gap-2 text-amber-400 font-bold">
                <Lock className="w-3.5 h-3.5" />
                <span>Owner Role Required</span>
              </div>
              <p className="text-[11px] text-neutral-400 leading-relaxed">
                Billing and payment method controls are restricted to <strong>Organization Owners</strong>.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Team Members List & Management */}
      <div
        className="p-5 rounded-sm space-y-4"
        style={{ background: "#13141f", border: "1px solid rgba(255,255,255,0.07)" }}
      >
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              WORKSPACE TEAM MEMBERS ({members.length})
            </span>
          </div>

          {perms.canManageTeam ? (
            <button
              onClick={() => setIsInviteModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-mono font-bold transition-all shadow-md shadow-purple-950/40 active:scale-95"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>+ Add Member</span>
            </button>
          ) : (
            <span className="text-[11px] font-mono text-neutral-500">
              Read-Only (Admin Role Required to Edit)
            </span>
          )}
        </div>

        <div className="divide-y divide-white/5 font-mono text-xs">
          {members.map((member) => {
            const memberPerms = getGitHubRolePermissions(member.role);
            return (
              <div key={member.id} className="py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-[220px]">
                  <div className="w-8 h-8 rounded-xl bg-purple-600/20 text-purple-300 font-bold flex items-center justify-center border border-purple-500/30 shrink-0">
                    {member.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="truncate">
                    <div className="font-bold text-white flex items-center gap-2 truncate">
                      <span>{member.name}</span>
                      {member.isSelf && (
                        <span className="text-[9px] text-neutral-400 font-normal px-1 py-0.2 rounded bg-white/5">
                          You
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-neutral-400 truncate">{member.email}</div>
                  </div>
                </div>

                {/* Role Selector or Display */}
                <div className="flex items-center gap-3">
                  {perms.canManageTeam && !member.isSelf ? (
                    <select
                      value={member.role}
                      onChange={(e) => handleRoleChange(member.id, e.target.value as GitHubRole)}
                      className="bg-[#181A24] border border-white/15 rounded-lg px-2.5 py-1 text-xs text-white font-mono focus:outline-none focus:border-purple-500 cursor-pointer"
                    >
                      <option value="owner">Owner (Root Admin)</option>
                      <option value="admin">Admin (Manage Team & Policy)</option>
                      <option value="developer">Developer (Write & Deploy)</option>
                      <option value="read">Auditor (Read Only)</option>
                    </select>
                  ) : (
                    <span className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase border ${memberPerms.badgeColor}`}>
                      {memberPerms.roleLabel}
                    </span>
                  )}

                  {/* Remove Member Button */}
                  {perms.canManageTeam && !member.isSelf && (
                    <button
                      onClick={() => handleRemoveMember(member.id)}
                      className="p-1 rounded-lg text-neutral-500 hover:text-red-400 hover:bg-red-950/30 transition-colors"
                      title="Remove Member from Workspace"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Invite Member Modal */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#14151E] border border-white/15 rounded-2xl p-6 shadow-2xl space-y-4 font-mono">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-purple-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Invite Workspace Member
                </h3>
              </div>
              <button
                onClick={() => setIsInviteModalOpen(false)}
                className="text-neutral-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {inviteError && (
              <div className="p-2.5 bg-red-950/50 border border-red-800/60 rounded-xl text-xs text-red-300">
                {inviteError}
              </div>
            )}

            <form onSubmit={handleAddMember} className="space-y-3.5">
              <div>
                <label className="block text-[11px] text-neutral-400 mb-1 font-semibold">
                  Member Full Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Sarah Connor"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  className="w-full bg-[#1A1C28] border border-white/15 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] text-neutral-400 mb-1 font-semibold">
                  Email Address
                </label>
                <input
                  type="email"
                  placeholder="sarah@nuuvixx.ai"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full bg-[#1A1C28] border border-white/15 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] text-neutral-400 mb-1 font-semibold">
                  Assign Workspace Role
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as GitHubRole)}
                  className="w-full bg-[#1A1C28] border border-white/15 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500 cursor-pointer"
                >
                  <option value="owner">Owner (Full Org & Billing Control)</option>
                  <option value="admin">Admin (Manage Team & Safety Policies)</option>
                  <option value="developer">Developer (Write & Deploy Agents)</option>
                  <option value="read">Auditor (Read-Only Traces & Audit Logs)</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setIsInviteModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs text-neutral-400 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-500 transition-all shadow-md shadow-purple-950/50"
                >
                  Add Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
