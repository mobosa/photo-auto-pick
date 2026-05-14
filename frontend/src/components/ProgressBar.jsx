import React from 'react';

const styles = {
  container: {
    background: '#18181b',
    borderRadius: 12,
    padding: 32,
    marginBottom: 24,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  spinner: {
    width: 18,
    height: 18,
    border: '2px solid #3f3f46',
    borderTop: '2px solid #a78bfa',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  title: {
    fontSize: 15,
    fontWeight: 600,
    color: '#e4e4e7',
  },
  pct: {
    fontSize: 22,
    fontWeight: 700,
    color: '#a78bfa',
    fontFamily: 'monospace',
  },
  barBg: {
    height: 12,
    background: '#27272a',
    borderRadius: 6,
    overflow: 'hidden',
    position: 'relative',
  },
  barFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #7c3aed, #a78bfa)',
    borderRadius: 6,
    transition: 'width 0.5s ease',
    position: 'relative',
  },
  barShimmer: {
    position: 'absolute',
    inset: 0,
    background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%)',
    animation: 'shimmer 2s ease-in-out infinite',
  },
  barFillError: {
    background: 'linear-gradient(90deg, #dc2626, #f87171)',
  },
  barFillCompleted: {
    background: 'linear-gradient(90deg, #16a34a, #4ade80)',
  },
  stats: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 14,
    fontSize: 13,
    color: '#71717a',
  },
  currentFile: {
    fontSize: 13,
    color: '#a1a1aa',
    marginTop: 10,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    minHeight: 20,
  },
  fileName: {
    color: '#c4b5fd',
    fontFamily: 'monospace',
    fontSize: 12,
    maxWidth: 400,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  errorText: {
    fontSize: 13,
    color: '#ef4444',
    marginTop: 10,
  },
  statusBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    background: '#1e1b2e',
    borderRadius: 6,
    fontSize: 12,
    color: '#a78bfa',
  },
};

// Inject keyframes once
const styleId = 'pb-keyframes';
if (typeof document !== 'undefined' && !document.getElementById(styleId)) {
  const el = document.createElement('style');
  el.id = styleId;
  el.textContent = `
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes shimmer { 0%,100% { transform: translateX(-100%); } 50% { transform: translateX(100%); } }
  `;
  document.head.appendChild(el);
}

const statusLabels = {
  pending: '准备中',
  processing: '分析中',
  completed: '分析完成',
  failed: '分析失败',
};

export default function ProgressBar({ status }) {
  const isFailed = status.status === 'failed';
  const isCompleted = status.status === 'completed';
  const isProcessing = status.status === 'processing' || status.status === 'pending';

  const total = status.total || 0;
  const processed = status.processed || 0;
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0;

  const barStyle = isFailed
    ? { ...styles.barFill, ...styles.barFillError, width: `${pct}%` }
    : isCompleted
      ? { ...styles.barFill, ...styles.barFillCompleted, width: '100%' }
      : { ...styles.barFill, width: `${pct}%` };

  return (
    <div style={styles.container}>
      {/* Header: title + percentage */}
      <div style={styles.header}>
        <div style={styles.titleRow}>
          {isProcessing && <div style={styles.spinner} />}
          <span style={styles.title}>
            {statusLabels[status.status] || status.status}
          </span>
          {isProcessing && (
            <span style={styles.statusBar}>
              {processed} / {total}
            </span>
          )}
        </div>
        <span style={styles.pct}>{pct}%</span>
      </div>

      {/* Progress bar */}
      <div style={styles.barBg}>
        <div style={barStyle}>
          {isProcessing && <div style={styles.barShimmer} />}
        </div>
      </div>

      {/* Stats row */}
      <div style={styles.stats}>
        <span>
          {isFailed
            ? `已完成 ${processed} / ${total} 张`
            : isCompleted
              ? `全部 ${total} 张分析完成`
              : `已处理 ${processed} / ${total} 张`}
        </span>
        {isProcessing && total > 0 && processed > 0 && (
          <span>
            预计剩余 {Math.max(0, Math.ceil((total - processed) * 1.5))}s
          </span>
        )}
      </div>

      {/* Current file */}
      {isProcessing && status.current_file && (
        <div style={styles.currentFile}>
          <span>正在处理:</span>
          <span style={styles.fileName}>{status.current_file}</span>
        </div>
      )}

      {/* Error message */}
      {isFailed && status.current_file && (
        <div style={styles.errorText}>{status.current_file}</div>
      )}
    </div>
  );
}
