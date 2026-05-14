import React, { useEffect, useState } from 'react';
import { getHistory, deleteTask } from '../api';

const styles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
    display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 200,
  },
  modal: {
    background: '#18181b', borderRadius: 16, width: '90%', maxWidth: 600,
    maxHeight: '80vh', overflow: 'auto', padding: 24, border: '1px solid #27272a',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20,
  },
  title: { fontSize: 18, fontWeight: 600, color: '#e4e4e7' },
  closeBtn: { background: 'none', border: 'none', color: '#71717a', fontSize: 24, cursor: 'pointer' },
  row: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '12px 16px', background: '#1e1e22', borderRadius: 8, marginBottom: 8,
  },
  rowLeft: { flex: 1, cursor: 'pointer' },
  taskId: { fontSize: 14, fontWeight: 600, color: '#a78bfa' },
  meta: { fontSize: 12, color: '#71717a' },
  score: { fontSize: 16, fontWeight: 700, marginLeft: 16 },
  delBtn: {
    background: 'none', border: 'none', color: '#71717a', fontSize: 16,
    cursor: 'pointer', padding: '4px 8px', marginLeft: 8,
  },
  delBtnHover: { color: '#ef4444' },
  empty: { textAlign: 'center', color: '#71717a', padding: 40 },
};

const scoreColor = (s) => s >= 80 ? '#22c55e' : s >= 60 ? '#eab308' : '#ef4444';

export default function HistoryPanel({ onSelect, onClose }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    getHistory().then(data => {
      setTasks(data.tasks || []);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (e, taskId) => {
    e.stopPropagation();
    if (!confirm('确认删除该条历史记录？')) return;
    try {
      await deleteTask(taskId);
      setTasks(prev => prev.filter(t => t.task_id !== taskId));
    } catch (err) {
      alert('删除失败: ' + err.message);
    }
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        <div style={styles.header}>
          <div style={styles.title}>历史评价记录</div>
          <button style={styles.closeBtn} onClick={onClose}>×</button>
        </div>
        {loading ? (
          <div style={styles.empty}>加载中...</div>
        ) : tasks.length === 0 ? (
          <div style={styles.empty}>暂无历史记录</div>
        ) : (
          tasks.map(t => (
            <div key={t.task_id} style={styles.row}>
              <div
                style={styles.rowLeft}
                onClick={() => { onSelect(t.task_id); onClose(); }}
              >
                <div style={styles.taskId}>任务 {t.task_id}</div>
                <div style={styles.meta}>
                  {t.photo_count} 张照片 · {t.created_at?.split('.')[0] || t.created_at}
                </div>
              </div>
              <div style={{ ...styles.score, color: scoreColor(t.avg_score) }}>
                {t.avg_score}
              </div>
              <button
                style={styles.delBtn}
                title="删除此记录"
                onClick={(e) => handleDelete(e, t.task_id)}
                onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                onMouseLeave={e => e.currentTarget.style.color = '#71717a'}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
