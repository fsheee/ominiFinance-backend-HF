'use client';

import React, { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  senderType: 'user' | 'system';
  senderName: string;
  text: string;
  badgeClass?: string;
  intent?: string;
}

interface Transaction {
  id: string;
  account_id: string;
  amount: number;
  merchant: string;
  category: string;
  location: string;
  velocity_mins: number;
  risk_score: number;
  status: 'PENDING_HITL' | 'APPROVED' | 'REJECTED' | 'COMPLETED';
  timestamp: string;
}

interface TelemetryData {
  status: string;
  sandbox_account: {
    id: string | null;
    currency: string | null;
    balance: number;
  };
  telemetry: {
    total_transactions_logged: number;
    completed_transactions: number;
    pending_hitl_pauses: number;
  };
}

export default function Dashboard() {
  const [sessionId] = useState(() => 'sandbox_session_' + Math.random().toString(36).substring(2, 10));
  
  // App States
  const [balance, setBalance] = useState<number>(0.0);
  const [accountId, setAccountId] = useState<string>('Loading...');
  const [telemetry, setTelemetry] = useState({
    total: 0,
    completed: 0,
    pending: 0,
  });
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      senderType: 'system',
      senderName: 'Central Orchestrator',
      text: `Hello! I am the Central Orchestrator. Submit your queries, and I will route them to my specialized sub-agents:
        <ul>
            <li><strong>Autonomous Expense Tracker</strong> for logging spending (e.g. <em>"Spent $45 on pizza at Domino's"</em>)</li>
            <li><strong>AI Fraud Detector</strong> to analyze risks and manage Human-In-The-Loop approvals</li>
            <li><strong>Financial Literacy Coach</strong> for concepts (e.g. <em>"Explain compound interest"</em>)</li>
        </ul>`,
      badgeClass: 'badge-orchestrator',
      intent: 'RAW_HTML',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isChatInputDisabled, setIsChatInputDisabled] = useState(false);
  const [thinkingMessageId, setThinkingMessageId] = useState<string | null>(null);
  
  // Toast Notification State
  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'warning' | 'error';
    show: boolean;
  }>({
    message: '',
    type: 'success',
    show: false,
  });

  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Dynamic API URL Helper for dev / prod compatibility
  const getApiUrl = (path: string) => {
    if (typeof window !== 'undefined' && window.location.port === '3000') {
      return `http://localhost:8000${path}`;
    }
    if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
      return `${process.env.NEXT_PUBLIC_API_URL}${path}`;
    }
    return path;
  };

  // Toast Handler
  const showToast = (message: string, type: 'success' | 'warning' | 'error' = 'success') => {
    setToast({ message, type, show: true });
  };

  // Auto-hide Toast
  useEffect(() => {
    if (toast.show) {
      const timer = setTimeout(() => {
        setToast((prev) => ({ ...prev, show: false }));
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [toast.show]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [messages, thinkingMessageId]);

  // Fetch Telemetry, Balance, and Ledger
  const [backendConnected, setBackendConnected] = useState<boolean>(true);

  const refreshBalance = async () => {
    try {
      const response = await fetch(getApiUrl('/wallet'));
      if (response.ok) {
        const data = await response.json();
        setBalance(data.balance);
        setAccountId(data.id);
        setBackendConnected(true);
      } else {
        setBackendConnected(false);
      }
    } catch (error) {
      setBackendConnected(false);
    }
  };

  const refreshTelemetry = async () => {
    try {
      const response = await fetch(getApiUrl('/api/telemetry'));
      if (response.ok) {
        const data: TelemetryData = await response.json();
        setTelemetry({
          total: data.telemetry.total_transactions_logged,
          completed: data.telemetry.completed_transactions,
          pending: data.telemetry.pending_hitl_pauses,
        });
        if (data.sandbox_account.balance !== undefined) {
          setBalance(data.sandbox_account.balance);
        }
        setBackendConnected(true);
      } else {
        setBackendConnected(false);
      }
    } catch (error) {
      setBackendConnected(false);
    }
  };

  const refreshLedger = async () => {
    try {
      const response = await fetch(getApiUrl('/transactions?limit=20'));
      if (response.ok) {
        const data = await response.json();
        setTransactions(data);
        setBackendConnected(true);
      } else {
        setBackendConnected(false);
      }
    } catch (error) {
      setBackendConnected(false);
    }
  };

  const refreshAll = () => {
    refreshBalance();
    refreshLedger();
    refreshTelemetry();
  };

  // Initial load and periodic polling
  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshTelemetry, 5000);
    return () => clearInterval(interval);
  }, []);

  // Reset Sandbox Database Handler
  const handleResetSandbox = async () => {
    if (!confirm('Are you sure you want to reset the database? This will clear all transactions and reset your balance to $5000.00 USD.')) {
      return;
    }
    try {
      const response = await fetch(getApiUrl('/reset'), { method: 'POST' });
      const result = await response.json();
      if (result.status === 'SUCCESS') {
        showToast('Database reset successfully!', 'success');
        setMessages([
          {
            id: 'reset-msg',
            senderType: 'system',
            senderName: 'Central Orchestrator',
            text: "Sandbox reset. Database cleared. Balance set to $5000.00 USD. Let's start fresh!",
            badgeClass: 'badge-orchestrator',
          },
        ]);
        refreshAll();
      } else {
        showToast('Reset failed: ' + result.message, 'error');
      }
    } catch (error) {
      console.error('Error resetting:', error);
      showToast('Network error during reset', 'error');
    }
  };

  // Handle HITL Decision (Approve / Reject)
  const handleHitlDecision = async (txId: string, approve: boolean) => {
    try {
      const response = await fetch(getApiUrl('/transactions/approve'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transaction_id: txId, approve }),
      });
      const result = await response.json();
      if (response.ok) {
        showToast(result.message, approve ? 'success' : 'warning');
        refreshAll();
        
        // Append result to chat
        const actionText = approve ? 'Approved' : 'Rejected';
        setMessages((prev) => [
          ...prev,
          {
            id: 'hitl-' + Date.now(),
            senderType: 'system',
            senderName: 'Central Orchestrator',
            text: `Human-In-The-Loop action completed: transaction <strong>${txId.substring(0, 8)}...</strong> has been <strong>${actionText.toUpperCase()}</strong>. Balance adjusted accordingly.`,
            badgeClass: 'badge-orchestrator',
            intent: 'RAW_HTML',
          },
        ]);
      } else {
        showToast(result.detail || 'Action failed', 'error');
      }
    } catch (error) {
      console.error('Error submitting HITL:', error);
      showToast('Network error during approval', 'error');
    }
  };

  // Submit Chat Message
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = inputValue.trim();
    if (!prompt) return;

    // Append User Message
    const userMsgId = 'msg-' + Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: userMsgId,
        senderType: 'user',
        senderName: 'You',
        text: prompt,
      },
    ]);
    setInputValue('');
    setIsChatInputDisabled(true);

    // Create thinking state
    const currentThinkingId = 'thinking-' + Date.now();
    setThinkingMessageId(currentThinkingId);

    try {
      const response = await fetch(getApiUrl('/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, session_id: sessionId }),
      });

      const result = await response.json();
      setThinkingMessageId(null);
      setIsChatInputDisabled(false);
      
      // Focus back on input
      setTimeout(() => chatInputRef.current?.focus(), 50);

      if (response.ok) {
        handleAgentResponse(result);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: 'err-' + Date.now(),
            senderType: 'system',
            senderName: 'System Error',
            text: 'Failed to process request: ' + (result.detail || 'Unknown error'),
            badgeClass: 'badge-fraud',
          },
        ]);
      }
    } catch (error) {
      setThinkingMessageId(null);
      setIsChatInputDisabled(false);
      setTimeout(() => chatInputRef.current?.focus(), 50);
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: 'err-' + Date.now(),
          senderType: 'system',
          senderName: 'System Error',
          text: 'Network error. Please make sure the server is running.',
          badgeClass: 'badge-fraud',
        },
      ]);
    }
  };

  // Parse Orchestrator Response and route badge details
  const handleAgentResponse = (res: { intent: string; message: string }) => {
    const intent = res.intent;
    const msg = res.message;

    let agentName = 'Central Orchestrator';
    let badgeClass = 'badge-orchestrator';

    if (intent === 'EXPENSE') {
      agentName = 'Expense Router Pipeline';
      badgeClass = 'badge-tracker';
      refreshAll();
    } else if (intent === 'FRAUD') {
      agentName = 'AI Fraud Detection Agent';
      badgeClass = 'badge-fraud';
    } else if (intent === 'LITERACY') {
      agentName = 'Financial Literacy Coach';
      badgeClass = 'badge-coach';
    } else if (intent === 'WALLET') {
      agentName = 'Central Orchestrator';
      badgeClass = 'badge-orchestrator';
      refreshAll();
    }

    setMessages((prev) => [
      ...prev,
      {
        id: 'reply-' + Date.now(),
        senderType: 'system',
        senderName: agentName,
        text: msg,
        badgeClass,
        intent,
      },
    ]);
  };

  // HTML escaping utility for React rendering
  const escapeHtml = (string: string) => {
    return String(string)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  // Parse text content and format inline jargon definitions
  const renderMessageContent = (msg: Message) => {
    if (msg.intent === 'RAW_HTML') {
      return <div className="msg-text" dangerouslySetInnerHTML={{ __html: msg.text }} />;
    }

    let text = escapeHtml(msg.text);

    if (msg.intent === 'LITERACY') {
      text = text.replace(/&lt;br&gt;/g, '<br>').replace(/\n/g, '<br>');
      
      const terms = [
        'compound interest', 'liquidity', 'diversification',
        'inflation', 'budgeting', 'yield', 'asset allocation',
      ];

      terms.forEach((term) => {
        const escapedTerm = term.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        const regex = new RegExp(`(${escapedTerm})\\s*\\(([^)]+)\\)`, 'gi');
        text = text.replace(regex, (match, word, analogy) => {
          return `<span class="jargon-term">${word}</span> <span class="analogy-block">(${analogy})</span>`;
        });
      });
    } else {
      text = text.replace(/\n/g, '<br>');
    }

    return <div className="msg-text" dangerouslySetInnerHTML={{ __html: text }} />;
  };

  // Map category to CSS classes & FontAwesome icon name
  const getCategoryIcon = (category: string) => {
    const cat = category.toLowerCase();
    if (cat.includes('food') || cat.includes('dining')) return 'fa-utensils';
    if (cat.includes('transport')) return 'fa-car-side';
    if (cat.includes('entertainment')) return 'fa-film';
    if (cat.includes('shopping')) return 'fa-bag-shopping';
    if (cat.includes('utility') || cat.includes('bill')) return 'fa-file-invoice-dollar';
    return 'fa-receipt';
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo">
          <i className="fa-solid fa-building-columns brand-icon"></i>
          <span className="brand-text">
            Omni<span className="highlight">Finance</span>
          </span>
          <span className="badge sandbox-badge">AI Sandbox</span>
        </div>
        <div className="header-actions">
          <button id="reset-db-btn" className="btn btn-secondary-neon" onClick={handleResetSandbox}>
            <i className="fa-solid fa-rotate-right"></i> Reset Sandbox
          </button>
        </div>
      </header>

      {/* Connection Error Banner */}
      {!backendConnected && (
        <div className="connection-banner">
          <i className="fa-solid fa-triangle-exclamation"></i>
          Cannot connect to backend at <code>localhost:8000</code>. Make sure the FastAPI server is running (<code>uvicorn main:app --reload</code>).
        </div>
      )}

      {/* Main Body */}
      <main className="app-body">
        
        {/* Left Side: Chat Workspace */}
        <section className="panel panel-chat">
          <div className="panel-header">
            <i className="fa-solid fa-comments"></i>
            <h2>Agent Routing Workspace</h2>
            <span className="active-pulse"></span>
          </div>

          <div id="chat-messages" className="chat-messages" ref={chatMessagesRef}>
            {messages.map((msg) => {
              let avatarIcon = msg.senderType === 'user' ? 'fa-user' : 'fa-robot';
              if (msg.badgeClass === 'badge-coach') avatarIcon = 'fa-graduation-cap';
              else if (msg.badgeClass === 'badge-tracker') avatarIcon = 'fa-tags';
              else if (msg.badgeClass === 'badge-fraud') avatarIcon = 'fa-shield-halved';

              return (
                <div
                  key={msg.id}
                  className={`message ${msg.senderType === 'user' ? 'user-message' : 'system-message'}`}
                >
                  <div className="msg-avatar">
                    <i className={`fa-solid ${avatarIcon}`}></i>
                  </div>
                  <div className="msg-content">
                    {msg.badgeClass ? (
                      <span className={`agent-badge ${msg.badgeClass}`}>{msg.senderName}</span>
                    ) : (
                      <span className="sender-name">{msg.senderName}</span>
                    )}
                    {renderMessageContent(msg)}
                  </div>
                </div>
              );
            })}

            {/* Thinking Indicator */}
            {thinkingMessageId && (
              <div className="message system-message" id={thinkingMessageId}>
                <div className="msg-avatar">
                  <i className="fa-solid fa-spinner fa-spin"></i>
                </div>
                <div className="msg-content">
                  <span className="sender-name">Central Orchestrator</span>
                  <div className="msg-text" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    Routing and parsing query...
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="chat-input-area">
            <form id="chat-form" onSubmit={handleChatSubmit}>
              <input
                type="text"
                id="chat-input"
                ref={chatInputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask a financial question or log an expense..."
                required
                autoComplete="off"
                disabled={isChatInputDisabled}
              />
              <button type="submit" className="btn btn-primary-neon" disabled={isChatInputDisabled}>
                <i className="fa-solid fa-paper-plane"></i>
              </button>
            </form>
          </div>
        </section>

        {/* Right Side: Wallet, Telemetry & Ledger */}
        <section className="panel panel-dashboard">
          
          <div className="dashboard-grid">
            {/* Balance Card */}
            <div className="card card-wallet">
              <div className="card-overlay"></div>
              <div className="card-header">
                <span>Digital Wallet Balance</span>
                <i className="fa-solid fa-wallet card-icon"></i>
              </div>
              <div className="balance-display">
                <span id="wallet-balance">
                  ${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="currency">USD</span>
              </div>
              <div className="account-meta">
                <span>
                  ID: <span id="account-id">{accountId}</span>
                </span>
              </div>
            </div>

            {/* Telemetry Stats Card */}
            <div className="card card-telemetry">
              <div className="card-header">
                <span>Sandbox Telemetry</span>
                <i className="fa-solid fa-chart-line card-icon"></i>
              </div>
              <div className="telemetry-stats">
                <div className="stat-item">
                  <div className="stat-value" id="stat-total-tx">
                    {telemetry.total}
                  </div>
                  <div className="stat-label">Transactions</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value" id="stat-completed-tx">
                    {telemetry.completed}
                  </div>
                  <div className="stat-label">Completed</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value text-warning" id="stat-pending-hitl" style={{ color: telemetry.pending > 0 ? 'var(--neon-orange)' : '' }}>
                    {telemetry.pending}
                  </div>
                  <div className="stat-label">Pending HITL</div>
                </div>
              </div>
            </div>
          </div>

          {/* Ledger Table */}
          <div className="ledger-container">
            <div className="panel-header">
              <i className="fa-solid fa-list-check"></i>
              <h2>Live Ledger Database</h2>
            </div>

            {transactions.length === 0 ? (
              <div id="ledger-empty" className="ledger-empty">
                <i className="fa-solid fa-receipt"></i>
                <p>No transactions logged in the sandbox database.</p>
              </div>
            ) : (
              <div id="ledger-list" className="ledger-list">
                {transactions.map((tx) => {
                  const icon = getCategoryIcon(tx.category);
                  const dateObj = new Date(tx.timestamp);
                  const dateStr =
                    dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
                    ' ' +
                    dateObj.toLocaleDateString([], { month: 'short', day: 'numeric' });

                  let riskClass = 'risk-low';
                  if (tx.risk_score > 75) riskClass = 'risk-high';
                  else if (tx.risk_score > 30) riskClass = 'risk-medium';

                  return (
                    <div
                      key={tx.id}
                      className={`ledger-item status-${tx.status.toLowerCase()}`}
                    >
                      <div className="ledger-left">
                        <div className="category-icon">
                          <i className={`fa-solid ${icon}`}></i>
                        </div>
                        <div className="tx-details">
                          <span className="tx-merchant">{tx.merchant}</span>
                          <div className="tx-meta">
                            <span>{dateStr}</span>
                            <span>•</span>
                            <span>{tx.category}</span>
                            <span>•</span>
                            <span className={`risk-badge ${riskClass}`}>
                              Risk: {tx.risk_score}%
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="ledger-right">
                        <span className="tx-amount">-${tx.amount.toFixed(2)}</span>
                        {tx.status === 'PENDING_HITL' ? (
                          <div className="hitl-actions">
                            <button
                              className="btn btn-hitl btn-hitl-approve btn-approve"
                              onClick={() => handleHitlDecision(tx.id, true)}
                              title="Approve Transaction"
                            >
                              <i className="fa-solid fa-check"></i>
                            </button>
                            <button
                              className="btn btn-hitl btn-hitl-reject btn-reject"
                              onClick={() => handleHitlDecision(tx.id, false)}
                              title="Reject Transaction"
                            >
                              <i className="fa-solid fa-xmark"></i>
                            </button>
                          </div>
                        ) : (
                          <span className={`status-badge status-${tx.status.toLowerCase()}`}>
                            {tx.status}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

      </main>

      {/* Notification Toast */}
      {toast.show && (
        <div
          id="toast"
          className="toast"
          style={{
            borderColor:
              toast.type === 'error'
                ? 'var(--neon-red)'
                : toast.type === 'warning'
                ? 'var(--neon-orange)'
                : 'var(--neon-cyan)',
          }}
        >
          <i
            className={`fa-solid ${
              toast.type === 'error'
                ? 'fa-circle-exclamation'
                : toast.type === 'warning'
                ? 'fa-triangle-exclamation'
                : 'fa-circle-check'
            }`}
            style={{
              color:
                toast.type === 'error'
                  ? 'var(--neon-red)'
                  : toast.type === 'warning'
                  ? 'var(--neon-orange)'
                  : 'var(--neon-cyan)',
            }}
          ></i>{' '}
          {toast.message}
        </div>
      )}
    </div>
  );
}
