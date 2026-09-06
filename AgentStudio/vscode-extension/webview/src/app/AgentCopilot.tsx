import * as React from 'react';
import { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/copilot.css';
import { postVsCodeMessage } from '../services/vscodeApi';

export interface ProposedCommand {
  commandType: string;
  args: Record<string, any>;
}

export interface CopilotProposal {
  proposalId: string;
  summary: string;
  commands: ProposedCommand[];
  diffYaml?: string;
}

export type CopilotMessage =
  | { id?: string; type: 'text'; role: 'user' | 'assistant'; content: string; timestamp: string }
  | { id?: string; type: 'proposal'; role: 'assistant'; proposal: CopilotProposal; timestamp: string }
  | { id?: string; type: 'run'; role: 'assistant'; content?: string; text?: string; terminal?: string; timestamp: string };

function formatTime(): string {
  const d = new Date();
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
}

const ProposalCard: React.FC<{
  proposal: CopilotProposal;
  onAccept: () => void;
  onReject: () => void;
}> = ({ proposal, onAccept, onReject }) => {
  const [status, setStatus] = useState<'pending' | 'accepted' | 'rejected'>('pending');

  return (
    <div className="copilot-changes-card" style={{ borderColor: 'var(--av-indigo)', background: 'var(--av-bg-elevated)', borderRadius: 6, padding: 10, marginTop: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontWeight: 600, fontSize: 11, color: '#A5B4FC' }}>
          [PROPOSED MODIFICATION] Review Required
        </span>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--av-text-muted)' }}>
          {proposal.commands.length} command{proposal.commands.length > 1 ? 's' : ''}
        </span>
      </div>

      <div style={{ fontSize: 11, color: 'var(--av-text-primary)', whiteSpace: 'pre-wrap', marginBottom: 10, lineHeight: 1.4 }}>
        {proposal.summary}
      </div>

      {status === 'pending' ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="av-btn av-btn-primary"
            style={{ fontSize: 11, padding: '4px 12px' }}
            onClick={() => {
              setStatus('accepted');
              onAccept();
            }}
          >
            ✓ Accept & Apply
          </button>
          <button
            className="av-btn av-btn-ghost"
            style={{ fontSize: 11, padding: '4px 12px' }}
            onClick={() => {
              setStatus('rejected');
              onReject();
            }}
          >
            ✕ Reject
          </button>
        </div>
      ) : (
        <div style={{ fontSize: 11, fontWeight: 600, color: status === 'accepted' ? '#10B981' : '#EF4444' }}>
          {status === 'accepted' ? '✓ Proposal Accepted & Applied to AST' : '✕ Proposal Rejected'}
        </div>
      )}
    </div>
  );
};

export const AgentCopilot: React.FC = () => {
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      type: 'text',
      role: 'assistant',
      content: 'AgentVerse Copilot active (Safe AST Mode: LLM → Proposal → User Approval → Apply).',
      timestamp: formatTime(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Listen for messages from Extension Host Core
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      const msg = e.data;
      if (msg?.type === 'COPILOT_PROPOSAL') {
        const proposalMsg: CopilotMessage = {
          type: 'proposal',
          role: 'assistant',
          proposal: {
            proposalId: msg.proposalId,
            summary: msg.summary,
            commands: msg.commands,
            diffYaml: msg.diffYaml,
          },
          timestamp: formatTime(),
        };
        setMessages((prev) => [...prev, proposalMsg]);
        setIsProcessing(false);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isProcessing) return;

    const userMsg: CopilotMessage = {
      type: 'text',
      role: 'user',
      content: trimmed,
      timestamp: formatTime(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsProcessing(true);

    // Send COPILOT_PROMPT request to extension core
    postVsCodeMessage({
      type: 'COPILOT_PROMPT',
      prompt: trimmed,
    });
  }, [input, isProcessing]);

  const handleAcceptProposal = (commands: ProposedCommand[]) => {
    postVsCodeMessage({
      type: 'ACCEPT_COPILOT_PROPOSAL',
      commands,
    });
  };

  return (
    <div className="copilot-root" style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--av-bg-panel)', fontFamily: 'var(--av-font-ui)' }}>
      {/* Header */}
      <div className="copilot-header" style={{ padding: '8px 12px', borderBottom: '1px solid var(--av-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', color: 'var(--av-text-secondary)' }}>
          Agent Copilot (Safe AI)
        </span>
        <span style={{ fontSize: 10, color: '#10B981', display: 'flex', alignItems: 'center', gap: 4 }}>
          ● Validation Active
        </span>
      </div>

      {/* Messages Thread */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{ fontSize: 10, color: 'var(--av-text-muted)', marginBottom: 2 }}>{msg.timestamp}</div>
            {msg.type === 'text' && (
              <div
                style={{
                  background: msg.role === 'user' ? '#6366F1' : 'var(--av-bg-elevated)',
                  color: msg.role === 'user' ? '#FFF' : 'var(--av-text-primary)',
                  padding: '8px 12px',
                  borderRadius: 6,
                  maxWidth: '85%',
                  fontSize: 12,
                  lineHeight: 1.4,
                }}
              >
                {msg.content}
              </div>
            )}
            {msg.type === 'proposal' && (
              <ProposalCard
                proposal={msg.proposal}
                onAccept={() => handleAcceptProposal(msg.proposal.commands)}
                onReject={() => {}}
              />
            )}
          </div>
        ))}

        {isProcessing && (
          <div style={{ fontSize: 11, color: 'var(--av-indigo)', fontStyle: 'italic' }}>
            Copilot analyzing manifest AST & formulating proposal...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <div style={{ padding: 10, borderTop: '1px solid var(--av-border)', display: 'flex', gap: 6 }}>
        <textarea
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Ask Copilot to change model, add search tools, or update budget..."
          style={{
            flex: 1,
            background: 'var(--av-bg-elevated)',
            color: 'var(--av-text-primary)',
            border: '1px solid var(--av-border)',
            borderRadius: 4,
            padding: 6,
            fontSize: 11,
          }}
        />
        <button
          className="av-btn av-btn-primary"
          onClick={handleSend}
          disabled={!input.trim() || isProcessing}
          style={{ fontSize: 12, padding: '0 14px' }}
        >
          Propose →
        </button>
      </div>
    </div>
  );
};

export default AgentCopilot;
