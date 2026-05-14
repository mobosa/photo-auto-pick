import React from 'react';

const styles = {
  container: {
    marginTop: 24,
  },
  header: {
    fontSize: 16,
    fontWeight: 600,
    color: '#a1a1aa',
    marginBottom: 16,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  count: {
    background: '#3f3f46',
    color: '#e4e4e7',
    fontSize: 12,
    padding: '2px 8px',
    borderRadius: 10,
    fontWeight: 500,
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  card: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: '14px 18px',
    background: '#18181b',
    borderRadius: 10,
    border: '1px solid #27272a',
    cursor: 'pointer',
    transition: 'border-color 0.15s, background 0.15s',
  },
  cardActive: {
    borderColor: '#7c3aed',
    background: '#1a1625',
  },
  cardHover: {
    borderColor: '#3f3f46',
    background: '#1e1e22',
  },
  icon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 18,
    flexShrink: 0,
  },
  iconProcessing: { background: '#1e1b2e' },
  iconCompleted: { background: '#052e16' },
  iconFailed: { background: '#2e0a0a' },
  iconPending: { background: '#1e1b2e' },
  body: {
    flex: 1,
    minWidth: 0,
  },
  name: {
    fontSize: 14,
    fontWeight: 600,
    color: '#e4e4e7',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    marginBottom: 6,
  },
  barBg: {
    height: 6,
    background: '#27272a',
    borderRadius: 3,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 3,
    transition: 'width 0.5s ease',
  },
  barProcessing: { background: 'linear-gradient(90deg, #7c3aed, #a78bfa)' },
  barCompleted: { background: '#22c55e' },
  barFailed: { background: '#ef4444' },
  barPending: { background: '#6366f1' },
  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginTop: 6,
    fontSize: 12,
    color: '#71717a',
  },
  statusBadge: {
    fontSize: 11,
    padding: '1px 8px',
    borderRadius: 4,
    fontWeight: 600,
  },
  badgeProcessing: { background: '#1e1b2e', color: '#a78bfa' },
  badgeCompleted: { background: '#052e16', color: '#4ade80' },
  badgeFailed: { background: '#2e0a0a', color: '#f87171' },
  badgePending: { background: '#1e1b2e', color: '#818cf8' },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flexShrink: 0,
  },
  pct: {
    fontSize: 18,
    fontWeight: 700,
    fontFamily: 'monospace',
    minWidth: 50,
    textAlign: 'right',
  },
  pctProcessing: { color: '#a78bfa' },
  pctCompleted: { color: '#4ade80' },
  pctFailed: { color: '#f87171' },
  pctPending: { color: '#818cf8' },
  removeBtn: {
    background: 'none',
    border: 'none',
    color: '#52525b',
    fontSize: 18,
    cursor: 'pointer',
    padding: '4px 6px',
    borderRadius: 4,
    lineHeight: 1,
    transition: 'color 0.15s',
  },
  fileCount: {
    fontSize: 13,
    fontWeight: 600,
    color: '#a1a1aa',
  },
  spinner: {
    width: 16,
    height: 16,
    border: '2px solid #3f3f46',
    borderTop: '2px solid #a78bfa',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    flexShrink: 0,
  },
};

const styleId = 'tl-spinner';
if (typeof document !== 'undefined' && !document.getElementById(styleId)) {
  const el = document.createElement('style');
  el.id = styleId;
  el.textContent = `@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
  document.head.appendChild(el);
}

const statusConfig = {
  pending:    { label: '准备中', icon: '⏳', badge: styles.badgePending,    pct: styles.pctPending,    bar: styles.barPending,    iconBg: styles.iconPending },
  processing: { label: '分析中', icon: '⚙',  badge: styles.badgeProcessing, pct: styles.pctProcessing, bar: styles.barProcessing, iconBg: styles.iconProcessing },
  completed:  { label: '已完成', icon: '✓',  badge: styles.badgeCompleted,  pct: styles.pctCompleted,  bar: styles.barCompleted,  iconBg: styles.iconCompleted },
  failed:     { label: '失败',   icon: '✕',  badge: styles.badgeFailed,     pct: styles.pctFailed,     bar: styles.barFailed,     iconBg: styles.iconFailed },
};

export default function TaskList({ tasks, activeTaskId, onSelectTask, onRemoveTask }) {
  const entries = Array.from(tasks.entries()).reverse(); // newest first

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        任务列表
        <span style={styles.count}>{entries.length}</span>
      </div>
      <div style={styles.list}>
        {entries.map(([tid, task]) => {
          const isActive = tid === activeTaskId;
          const st = task.status || {};
          const cfg = statusConfig[st.status] || statusConfig.pending;
          const total = st.total || 0;
          const processed = st.processed || 0;
          const pct = total > 0 ? Math.round((processed / total) * 100) : 0;
          const avgScore = task.results?.results?.length
            ? Math.round(task.results.results.reduce((s, r) => s + r.final_score, 0) / task.results.results.length)
            : null;

          return (
            <div
              key={tid}
              style={{ ...styles.card, ...(isActive ? styles.cardActive : {}) }}
              onClick={() => onSelectTask(tid)}
              onMouseEnter={e => { if (!isActive) { e.currentTarget.style.borderColor = '#3f3f46'; e.currentTarget.style.background = '#1e1e22'; } }}
              onMouseLeave={e => { if (!isActive) { e.currentTarget.style.borderColor = '#27272a'; e.currentTarget.style.background = '#18181b'; } }}
            >
              {/* Status icon */}
              <div style={{ ...styles.icon, ...cfg.iconBg }}>
                {st.status === 'processing' || st.status === 'pending' ? (
                  <div style={styles.spinner} />
                ) : (
                  <span>{cfg.icon}</span>
                )}
              </div>

              {/* Body */}
              <div style={styles.body}>
                <div style={styles.name}>{task.folderName || tid}</div>
                {/* Progress bar */}
                <div style={styles.barBg}>
                  <div style={{ ...styles.barFill, ...cfg.bar, width: `${st.status === 'completed' ? 100 : pct}%` }} />
                </div>
                <div style={styles.meta}>
                  <span style={{ ...styles.statusBadge, ...cfg.badge }}>{cfg.label}</span>
                  <span>{processed} / {total}</span>
                  {st.status === 'processing' && st.current_file && (
                    <span style={{ color: '#a78bfa', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {st.current_file}
                    </span>
                  )}
                </div>
              </div>

              {/* Right side */}
              <div style={styles.right}>
                {avgScore !== null && (
                  <span style={{ ...styles.fileCount, color: avgScore >= 80 ? '#4ade80' : avgScore >= 60 ? '#eab308' : '#f87171' }}>
                    均分 {avgScore}
                  </span>
                )}
                <span style={{ ...styles.pct, ...cfg.pct }}>{pct}%</span>
                <button
                  style={styles.removeBtn}
                  title="移除任务"
                  onClick={(e) => { e.stopPropagation(); onRemoveTask(tid); }}
                  onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                  onMouseLeave={e => e.currentTarget.style.color = '#52525b'}
                >
                  ×
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
