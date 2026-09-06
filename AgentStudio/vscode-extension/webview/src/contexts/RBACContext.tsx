import * as React from 'react';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { postVsCodeMessage } from '../services/vscodeApi';

export type UserRole = 'developer' | 'team_lead' | 'ciso' | 'auditor' | 'owner' | 'admin' | 'write' | 'read';

export interface IUserContext {
    username: string;
    role: UserRole;
    email: string;
    provider?: string;
    isAuthenticated?: boolean;
    assumedRoleArn?: string;
    userArn?: string;
}

interface RBACContextType {
    user: IUserContext | null;
    can: (action: string, resourceArn?: string) => boolean;
    setUserRole: (role: UserRole) => void;
    assumeIamRole: (roleArn: string) => void;
}

const RBACContext = createContext<RBACContextType>({
    user: null,
    can: () => false,
    setUserRole: () => {},
    assumeIamRole: () => {}
});

const ROLE_PERMISSIONS: Record<string, string[]> = {
    developer: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'deploy_staging', 'agentos:ExecuteAgent'],
    write: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'deploy_staging', 'agentos:ExecuteAgent'],
    team_lead: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'edit_policy', 'approve_staging', 'agentos:ExecuteAgent'],
    admin: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'edit_policy', 'approve_staging', 'approve_production', 'iam:ManageTeam', 'agentos:ExecuteAgent', 'agentos:DeployMicroVM'],
    owner: ['edit_prompt', 'run_locally', 'test_agent', 'view_dashboard', 'edit_policy', 'approve_staging', 'approve_production', 'iam:ManageTeam', 'billing:ManageSubscription', 'agentos:ExecuteAgent', 'agentos:DeployMicroVM'],
    ciso: ['view_dashboard', 'view_audit', 'approve_production', 'edit_policy'],
    auditor: ['view_dashboard', 'view_audit'],
    read: ['view_dashboard', 'view_audit']
};

export const RBACProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<IUserContext>({
        username: 'Loading identity...',
        role: 'team_lead',
        email: '...',
        provider: 'Local Identity',
        isAuthenticated: false,
        assumedRoleArn: 'arn:agentverse:iam::org_default:role/DeveloperRole',
        userArn: 'arn:agentverse:iam::org_default:user/developer'
    });

    useEffect(() => {
        postVsCodeMessage({ type: 'GET_AUTH_STATUS' });

        const handleMessage = (event: MessageEvent) => {
            const msg = event.data;
            if (msg.type === 'AUTH_STATUS_RESPONSE' && msg.user) {
                setUser(prev => ({
                    ...prev,
                    username: msg.user.username,
                    email: msg.user.email,
                    role: msg.user.role || prev.role,
                    provider: msg.user.provider,
                    isAuthenticated: msg.user.isAuthenticated,
                    assumedRoleArn: msg.user.assumedRoleArn || prev.assumedRoleArn,
                    userArn: msg.user.userArn || prev.userArn
                }));
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    const can = (action: string, resourceArn?: string): boolean => {
        if (!user) return false;
        const permissions = ROLE_PERMISSIONS[user.role] || [];

        // Direct action match or wildcard match
        const hasPermission = permissions.includes(action) || permissions.includes('*');
        if (!hasPermission) return false;

        // If resourceArn is specified, basic pattern check
        if (resourceArn && resourceArn.startsWith('arn:agentverse:')) {
            return true;
        }

        return true;
    };

    const setUserRole = (role: UserRole) => {
        const roleArnMap: Record<string, string> = {
            owner: 'arn:agentverse:iam::org_default:role/OwnerRole',
            admin: 'arn:agentverse:iam::org_default:role/AdminRole',
            developer: 'arn:agentverse:iam::org_default:role/DeveloperRole',
            auditor: 'arn:agentverse:iam::org_default:role/AuditorRole'
        };
        setUser((prev: IUserContext) => ({
            ...prev,
            role,
            assumedRoleArn: roleArnMap[role] || prev.assumedRoleArn
        }));
    };

    const assumeIamRole = (roleArn: string) => {
        const roleName = roleArn.split('/').pop() || '';
        const roleMap: Record<string, UserRole> = {
            OwnerRole: 'owner',
            AdminRole: 'admin',
            DeveloperRole: 'developer',
            AuditorRole: 'auditor'
        };
        const newRole = roleMap[roleName] || 'developer';
        setUser((prev: IUserContext) => ({
            ...prev,
            role: newRole,
            assumedRoleArn: roleArn
        }));
    };

    return (
        <RBACContext.Provider value={{ user, can, setUserRole, assumeIamRole }}>
            {children}
        </RBACContext.Provider>
    );
};

export const useRBAC = () => useContext(RBACContext);
