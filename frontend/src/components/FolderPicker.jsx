import React, { useEffect, useState } from 'react';
import { browseFolder } from '../api';

const styles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
    display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 200,
  },
  modal: {
    background: '#18181b', borderRadius: 16, width: '90%', maxWidth: 560,
    maxHeight: '75vh', display: 'flex', flexDirection: 'column',
    border: '1px solid #27272a',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '16px 20px', borderBottom: '1px solid #27272a',
  },
  title: { fontSize: 16, fontWeight: 600, color: '#e4e4e7' },
  closeBtn: { background: 'none', border: 'none', color: '#71717a', fontSize: 22, cursor: 'pointer' },
  breadcrumb: {
    padding: '8px 20px', background: '#111113', borderBottom: '1px solid #27272a',
    display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center',
  },
  crumb: {
    background: 'none', border: 'none', color: '#a78bfa', fontSize: 13,
    cursor: 'pointer', padding: '2px 4px', borderRadius: 4,
  },
  crumbSep: { color: '#3f3f46', fontSize: 12 },
  crumbCurrent: {
    background: 'none', border: 'none', color: '#e4e4e7', fontSize: 13,
    padding: '2px 4px',
  },
  list: {
    flex: 1, overflow: 'auto', padding: '8px 12px',
  },
  item: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '8px 12px', borderRadius: 6, cursor: 'pointer',
    fontSize: 14, color: '#e4e4e7', transition: 'background 0.1s',
  },
  icon: { fontSize: 16, width: 20, textAlign: 'center' },
  footer: {
    display: 'flex', justifyContent: 'flex-end', gap: 12,
    padding: '12px 20px', borderTop: '1px solid #27272a',
  },
  btn: {
    padding: '8px 20px', borderRadius: 6, fontSize: 14, cursor: 'pointer',
    fontWeight: 600, border: 'none',
  },
  btnPrimary: { background: '#7c3aed', color: '#fff' },
  btnSecondary: { background: '#27272a', color: '#a1a1aa', border: '1px solid #3f3f46' },
  empty: { textAlign: 'center', color: '#52525b', padding: 40, fontSize: 14 },
};

function _buildCrumbs(path) {
  if (!path) return [];
  const parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
  const crumbs = [];
  for (let i = 0; i < parts.length; i++) {
    // On Windows, first part is like "C:" — add backslash
    const p = i === 0 ? parts[i] + '\\' : parts.slice(0, i + 1).join('\\');
    crumbs.push({ label: parts[i], path: p });
  }
  return crumbs;
}

export default function FolderPicker({ onSelect, onClose }) {
  const [currentPath, setCurrentPath] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = (path) => {
    setLoading(true);
    browseFolder(path).then(data => {
      if (data.error) {
        setItems([]);
      } else {
        setCurrentPath(data.current || '');
        setItems(data.items || []);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(''); }, []);

  const crumbs = _buildCrumbs(currentPath);

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        <div style={styles.header}>
          <div style={styles.title}>选择文件夹</div>
          <button style={styles.closeBtn} onClick={onClose}>×</button>
        </div>

        {/* Breadcrumb navigation */}
        <div style={styles.breadcrumb}>
          <button style={styles.crumb} onClick={() => load('')}>此电脑</button>
          {crumbs.map((c, i) => (
            <React.Fragment key={i}>
              <span style={styles.crumbSep}>›</span>
              {i === crumbs.length - 1 ? (
                <span style={styles.crumbCurrent}>{c.label}</span>
              ) : (
                <button style={styles.crumb} onClick={() => load(c.path)}>{c.label}</button>
              )}
            </React.Fragment>
          ))}
        </div>

        <div style={styles.list}>
          {loading ? (
            <div style={styles.empty}>加载中...</div>
          ) : items.length === 0 ? (
            <div style={styles.empty}>此文件夹为空</div>
          ) : (
            items.map((item, i) => (
              <div
                key={i}
                style={styles.item}
                onClick={() => { if (item.is_dir) load(item.path); }}
                onMouseEnter={e => e.currentTarget.style.background = '#27272a'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={styles.icon}>{item.is_dir ? '📁' : '📄'}</span>
                <span>{item.name}</span>
              </div>
            ))
          )}
        </div>
        <div style={styles.footer}>
          <button style={{ ...styles.btn, ...styles.btnSecondary }} onClick={onClose}>取消</button>
          <button
            style={{ ...styles.btn, ...styles.btnPrimary, ...(!currentPath ? { opacity: 0.5 } : {}) }}
            disabled={!currentPath}
            onClick={() => currentPath && onSelect(currentPath)}
          >
            选择此文件夹
          </button>
        </div>
      </div>
    </div>
  );
}
