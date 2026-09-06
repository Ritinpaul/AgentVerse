import * as React from 'react';
import { useState, useEffect } from 'react';
import '../styles/ide-tokens.css';
import { postVsCodeMessage } from '../services/vscodeApi';

export interface UserSession {
  userId: string;
  email: string;
  name?: string;
  role?: string;
  orgName?: string;
  orgTier?: string;
  provider?: string;
}

interface Props {
  onSignedIn?: () => void;
}

export const SignInPanel: React.FC<Props> = ({ onSignedIn }) => {
  const [session, setSession] = useState<UserSession | null>(null);
  const [tab, setTab] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  useEffect(() => {
    // Request current auth session from extension host
    postVsCodeMessage({ type: 'GET_SESSION' });

    const handleMessage = (e: MessageEvent) => {
      const msg = e.data;
      if (!msg) return;

      if (msg.type === 'SESSION_STATE') {
        setSession(msg.session || null);
        setLoading(false);
      } else if (msg.type === 'AUTH_SUCCESS') {
        setSession(msg.session);
        setLoading(false);
        setError(null);
        setStatusNotice(`Welcome back, ${msg.session?.name || msg.session?.email}!`);
        setTimeout(() => setStatusNotice(null), 4000);
      } else if (msg.type === 'AUTH_ERROR') {
        setError(msg.error || 'Authentication error.');
        setLoading(false);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleSignIn = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!email.trim() || !password) {
      setError('Please provide email and password.');
      return;
    }
    setError(null);
    setLoading(true);
    postVsCodeMessage({
      type: 'SIGN_IN_CREDENTIALS',
      email: email.trim(),
      password,
    });
  };

  const handleSignUp = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!name.trim() || !email.trim() || !password) {
      setError('Name, email, and password are required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setError(null);
    setLoading(true);
    postVsCodeMessage({
      type: 'SIGN_UP_CREDENTIALS',
      name: name.trim(),
      email: email.trim(),
      password,
      orgName: orgName.trim() || undefined,
    });
  };

  const handleQuickLocalDev = () => {
    setError(null);
    setLoading(true);
    postVsCodeMessage({ type: 'SIGN_IN_LOCAL_DEV' });
  };

  const handleOAuth = (provider: 'google' | 'github') => {
    setError(null);
    postVsCodeMessage({ type: 'SIGN_IN_OAUTH', provider });
  };

  const handleSignOut = () => {
    setError(null);
    postVsCodeMessage({ type: 'SIGN_OUT' });
  };

  const fillDemoCredentials = () => {
    setEmail('developer@nuuvixx.ai');
    setPassword('demo-password');
    setError(null);
  };

  // ── 1. ACTIVE AUTHENTICATED PROFILE VIEW ─────────────────────────────────
  if (session) {
    const initials = (session.name || session.email)
      .split(' ')
      .map((s) => s[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();

    const roleBadgeColor =
      session.role === 'owner'
        ? 'var(--av-amber)'
        : session.role === 'admin'
        ? 'var(--av-indigo)'
        : 'var(--av-emerald)';

    return (
      <div className="av-signin-panel" style={{ padding: '16px 12px' }}>
        <div className="av-signin-card" style={{ gap: 16, width: '100%', maxWidth: 360, margin: '0 auto' }}>
          {/* Brand Header */}
          <div className="av-signin-logo" style={{ marginBottom: 4 }}>
            <div className="av-signin-logo-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="#B22222">
                <polygon points="12,2 22,22 2,22" />
              </svg>
            </div>
            <span className="av-signin-logo-text">AgentVerse IDE</span>
          </div>

          {/* User Profile Card */}
          <div
            style={{
              background: 'var(--av-bg-card)',
              border: '1px solid var(--av-border)',
              borderRadius: 8,
              padding: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
              textAlign: 'left',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #B22222, #4F52C9)',
                  color: '#FFF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: 15,
                  position: 'relative',
                  flexShrink: 0,
                }}
              >
                {initials || 'AV'}
                <span
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    right: 0,
                    width: 10,
                    height: 10,
                    background: 'var(--av-emerald)',
                    borderRadius: '50%',
                    border: '2px solid var(--av-bg-panel)',
                  }}
                  title="Connected & Active"
                />
              </div>

              <div style={{ overflow: 'hidden', flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--av-text-heading)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {session.name || 'Agent Developer'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--av-text-secondary)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {session.email}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: 'rgba(255,255,255,0.06)',
                  color: roleBadgeColor,
                  border: `1px solid ${roleBadgeColor}44`,
                }}
              >
                {session.role || 'Developer'}
              </span>

              <span
                style={{
                  fontSize: 10,
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: 'rgba(255,255,255,0.04)',
                  color: 'var(--av-text-secondary)',
                  border: '1px solid var(--av-border)',
                }}
              >
                {session.orgName || 'Nuuvixx Workspace'}
              </span>

              <span
                style={{
                  fontSize: 10,
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: 'rgba(16, 185, 129, 0.1)',
                  color: 'var(--av-emerald)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                }}
              >
                {session.orgTier || 'Free / BYOK'}
              </span>
            </div>

            <div style={{ fontSize: 11, color: 'var(--av-text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
              <span style={{ color: 'var(--av-emerald)' }}>●</span>
              <span>Provider: {session.provider || 'AgentVerse Platform'}</span>
            </div>
          </div>

          {/* Quick Features Overview */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
              <span className="av-signin-check">✓</span>
              <span style={{ color: 'var(--av-text-secondary)' }}>Free model quota active (50k tokens/day)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
              <span className="av-signin-check">✓</span>
              <span style={{ color: 'var(--av-text-secondary)' }}>Workspace agent sync & live AST copilot</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
              <span className="av-signin-check">✓</span>
              <span style={{ color: 'var(--av-text-secondary)' }}>GovernOS security policies & audit trails</span>
            </div>
          </div>

          {statusNotice && (
            <div
              style={{
                fontSize: 12,
                color: 'var(--av-emerald)',
                background: 'var(--av-emerald-alpha)',
                padding: '8px 12px',
                borderRadius: 4,
                border: '1px solid var(--av-emerald-dim)',
              }}
            >
              {statusNotice}
            </div>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', marginTop: 4 }}>
            <button
              className="av-btn av-btn-ghost"
              style={{ width: '100%', fontSize: 12, justifyContent: 'center' }}
              onClick={() => postVsCodeMessage({ type: 'OPEN_SETTINGS' })}
            >
              Configure API Keys & Models
            </button>
            <button
              className="av-btn av-btn-secondary"
              style={{ width: '100%', fontSize: 12, justifyContent: 'center', color: '#EF4444' }}
              onClick={handleSignOut}
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── 2. LOGIN & REGISTRATION FORM VIEW ────────────────────────────────────
  return (
    <div className="av-signin-panel" style={{ padding: '16px 12px' }}>
      <div className="av-signin-card" style={{ width: '100%', maxWidth: 360, margin: '0 auto', gap: 14 }}>
        {/* Logo */}
        <div className="av-signin-logo">
          <div className="av-signin-logo-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="#B22222">
              <polygon points="12,2 22,22 2,22" />
            </svg>
          </div>
          <span className="av-signin-logo-text">AgentVerse IDE</span>
        </div>

        {/* Tab Switcher */}
        <div
          style={{
            display: 'flex',
            width: '100%',
            background: 'var(--av-bg-panel)',
            padding: 2,
            borderRadius: 6,
            border: '1px solid var(--av-border)',
          }}
        >
          <button
            style={{
              flex: 1,
              padding: '6px 0',
              fontSize: 12,
              fontWeight: tab === 'signin' ? 600 : 400,
              background: tab === 'signin' ? 'var(--av-bg-card)' : 'transparent',
              color: tab === 'signin' ? 'var(--av-text-heading)' : 'var(--av-text-secondary)',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onClick={() => {
              setTab('signin');
              setError(null);
            }}
          >
            Sign In
          </button>
          <button
            style={{
              flex: 1,
              padding: '6px 0',
              fontSize: 12,
              fontWeight: tab === 'signup' ? 600 : 400,
              background: tab === 'signup' ? 'var(--av-bg-card)' : 'transparent',
              color: tab === 'signup' ? 'var(--av-text-heading)' : 'var(--av-text-secondary)',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onClick={() => {
              setTab('signup');
              setError(null);
            }}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div
            style={{
              fontSize: 11,
              color: '#F87171',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              padding: '8px 10px',
              borderRadius: 4,
              textAlign: 'left',
              width: '100%',
              lineHeight: 1.4,
            }}
          >
            {error}
          </div>
        )}

        {/* Form Elements */}
        {tab === 'signin' ? (
          <form onSubmit={handleSignIn} style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
            <div style={{ textAlign: 'left' }}>
              <label style={{ fontSize: 11, color: 'var(--av-text-secondary)', display: 'block', marginBottom: 4 }}>
                Email Address
              </label>
              <input
                type="email"
                className="av-input"
                style={{ width: '100%', boxSizing: 'border-box' }}
                placeholder="name@organization.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div style={{ textAlign: 'left' }}>
              <label style={{ fontSize: 11, color: 'var(--av-text-secondary)', display: 'block', marginBottom: 4 }}>
                Password
              </label>
              <input
                type="password"
                className="av-input"
                style={{ width: '100%', boxSizing: 'border-box' }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <button
              type="submit"
              className="av-btn av-btn-primary"
              style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
              disabled={loading}
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>

            {/* Demo autofill hint */}
            <div style={{ textAlign: 'center', marginTop: 2 }}>
              <button
                type="button"
                onClick={fillDemoCredentials}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--av-indigo)',
                  fontSize: 11,
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 2,
                }}
              >
                Use demo credentials (developer@nuuvixx.ai)
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSignUp} style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
            <div style={{ textAlign: 'left' }}>
              <label style={{ fontSize: 11, color: 'var(--av-text-secondary)', display: 'block', marginBottom: 4 }}>
                Full Name
              </label>
              <input
                type="text"
                className="av-input"
                style={{ width: '100%', boxSizing: 'border-box' }}
                placeholder="Alex Vance"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div style={{ textAlign: 'left' }}>
              <label style={{ fontSize: 11, color: 'var(--av-text-secondary)', display: 'block', marginBottom: 4 }}>
                Work Email
              </label>
              <input
                type="email"
                className="av-input"
                style={{ width: '100%', boxSizing: 'border-box' }}
                placeholder="alex@enterprise.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div style={{ textAlign: 'left' }}>
              <label style={{ fontSize: 11, color: 'var(--av-text-secondary)', display: 'block', marginBottom: 4 }}>
                Organization / Team (Optional)
              </label>
              <input
                type="text"
                className="av-input"
                style={{ width: '100%', boxSizing: 'border-box' }}
                placeholder="Acme AI Labs"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                disabled={loading}
              />
            </div>

            <div style={{ textAlign: 'left' }}>
              <label style={{ fontSize: 11, color: 'var(--av-text-secondary)', display: 'block', marginBottom: 4 }}>
                Password (min 6 characters)
              </label>
              <input
                type="password"
                className="av-input"
                style={{ width: '100%', boxSizing: 'border-box' }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <button
              type="submit"
              className="av-btn av-btn-primary"
              style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
              disabled={loading}
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>
        )}

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: 8, margin: '4px 0' }}>
          <div style={{ flex: 1, height: 1, background: 'var(--av-border)' }} />
          <span style={{ fontSize: 10, color: 'var(--av-text-muted)', textTransform: 'uppercase' }}>or</span>
          <div style={{ flex: 1, height: 1, background: 'var(--av-border)' }} />
        </div>

        {/* 1-Click Local Dev Login */}
        <button
          type="button"
          className="av-btn av-btn-secondary"
          style={{ width: '100%', justifyContent: 'center', fontSize: 12 }}
          onClick={handleQuickLocalDev}
          disabled={loading}
          title="Instant offline developer login using system git identity"
        >
          1-Click Local Dev Session
        </button>

        {/* Social / SSO Auth */}
        <div style={{ display: 'flex', gap: 8, width: '100%' }}>
          <button
            type="button"
            className="av-btn av-btn-ghost"
            style={{ flex: 1, justifyContent: 'center', fontSize: 11 }}
            onClick={() => handleOAuth('google')}
            disabled={loading}
          >
            Google SSO
          </button>
          <button
            type="button"
            className="av-btn av-btn-ghost"
            style={{ flex: 1, justifyContent: 'center', fontSize: 11 }}
            onClick={() => handleOAuth('github')}
            disabled={loading}
          >
            GitHub SSO
          </button>
        </div>

        {/* Features footnote */}
        <div className="av-signin-features" style={{ width: '100%', marginTop: 6 }}>
          <div className="av-signin-feature">
            <span className="av-signin-check">✓</span>
            <span className="av-signin-feature-label">Free model quota</span>
            <span className="av-signin-feature-sub">BYOK & Free Models</span>
          </div>
          <div className="av-signin-feature">
            <span className="av-signin-check">✓</span>
            <span className="av-signin-feature-label">AST Copilot</span>
            <span className="av-signin-feature-sub">Safe Code Proposals</span>
          </div>
          <div className="av-signin-feature">
            <span className="av-signin-check">✓</span>
            <span className="av-signin-feature-label">GovernOS Guard</span>
            <span className="av-signin-feature-sub">Audit & Red-team</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignInPanel;
