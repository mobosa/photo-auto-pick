import React, { useState } from 'react';
import { thumbnailUrl } from '../api';

const gradeColors = { S: '#a855f7', A: '#22c55e', 'B+': '#3b82f6', B: '#06b6d4', 'C+': '#eab308', C: '#f97316', D: '#ef4444' };

const styles = {
  toolbar: {
    display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12,
  },
  toolBtn: {
    padding: '6px 16px', background: '#27272a', color: '#a1a1aa',
    border: '1px solid #3f3f46', borderRadius: 6, fontSize: 13, cursor: 'pointer',
  },
  toolBtnActive: { background: '#7c3aed', color: '#fff', borderColor: '#7c3aed' },
  toolBtnDanger: { background: '#dc2626', color: '#fff', border: 'none' },
  toolBtnDangerDisabled: { background: '#450a0a', color: '#7f1d1d', border: 'none', cursor: 'not-allowed' },
  grid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: 16, marginTop: 8,
  },
  card: {
    background: '#18181b', borderRadius: 10, overflow: 'hidden',
    cursor: 'pointer', transition: 'transform 0.15s, box-shadow 0.15s',
    border: '2px solid transparent', position: 'relative',
  },
  cardSelected: { borderColor: '#7c3aed' },
  img: { width: '100%', height: 160, objectFit: 'cover', background: '#27272a' },
  info: { padding: '10px 12px' },
  filename: {
    fontSize: 12, color: '#a1a1aa', overflow: 'hidden',
    textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 6,
  },
  scoreRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  score: { fontSize: 20, fontWeight: 700 },
  grade: {
    display: 'inline-block', padding: '2px 10px', borderRadius: 6,
    fontSize: 13, fontWeight: 700, color: '#fff',
  },
  checkbox: {
    position: 'absolute', top: 8, left: 8, width: 22, height: 22,
    borderRadius: 4, border: '2px solid #fff', background: 'rgba(0,0,0,0.4)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 14, color: '#fff', zIndex: 2,
  },
  empty: { textAlign: 'center', padding: 60, color: '#71717a' },
  count: { fontSize: 13, color: '#71717a' },
};

function PhotoGrid({ results, taskId, onSelect, onDelete }) {
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState(new Set());

  if (!results || results.length === 0) {
    return <div style={styles.empty}>暂无结果</div>;
  }

  const toggleSelect = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const selectAll = () => {
    if (selected.size === results.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(results.map(r => r.id)));
    }
  };

  const handleDelete = () => {
    if (selected.size === 0) return;
    onDelete(Array.from(selected));
    setSelected(new Set());
    setSelectMode(false);
  };

  return (
    <>
      {/* Toolbar */}
      <div style={styles.toolbar}>
        <button
          style={{ ...styles.toolBtn, ...(selectMode ? styles.toolBtnActive : {}) }}
          onClick={() => { setSelectMode(!selectMode); setSelected(new Set()); }}
        >
          {selectMode ? '取消选择' : '选择模式'}
        </button>
        {selectMode && (
          <>
            <button style={styles.toolBtn} onClick={selectAll}>
              {selected.size === results.length ? '取消全选' : '全选'}
            </button>
            <button
              style={selected.size > 0 ? { ...styles.toolBtn, ...styles.toolBtnDanger }
                : { ...styles.toolBtn, ...styles.toolBtnDangerDisabled }}
              disabled={selected.size === 0}
              onClick={handleDelete}
            >
              删除选中 ({selected.size})
            </button>
            <span style={styles.count}>
              {selected.size > 0 ? `已选 ${selected.size} / ${results.length} 张` : `${results.length} 张照片`}
            </span>
          </>
        )}
      </div>

      {/* Grid */}
      <div style={styles.grid}>
        {results.map(photo => (
          <div
            key={photo.id}
            style={{
              ...styles.card,
              ...(selected.has(photo.id) ? styles.cardSelected : {}),
            }}
            onClick={() => selectMode ? toggleSelect(photo.id) : onSelect(photo)}
            onMouseEnter={e => {
              if (!selectMode) {
                e.currentTarget.style.transform = 'translateY(-3px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.4)';
              }
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {selectMode && (
              <div style={styles.checkbox}>
                {selected.has(photo.id) ? '✓' : ''}
              </div>
            )}
            <img
              src={thumbnailUrl(taskId, photo.filename)}
              alt={photo.filename} style={styles.img} loading="lazy"
            />
            <div style={styles.info}>
              <div style={styles.filename} title={photo.filename}>{photo.filename}</div>
              <div style={styles.scoreRow}>
                <span style={{ ...styles.score, color: gradeColors[photo.grade] || '#e4e4e7' }}>
                  {photo.final_score}
                </span>
                <span style={{ ...styles.grade, background: gradeColors[photo.grade] || '#71717a' }}>
                  {photo.grade}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default React.memo(PhotoGrid, (prev, next) => {
  return prev.results === next.results && prev.taskId === next.taskId
    && prev.onSelect === next.onSelect && prev.onDelete === next.onDelete;
});
