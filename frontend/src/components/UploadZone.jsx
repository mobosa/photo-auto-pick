import React, { useRef, useState } from 'react';
import FolderPicker from './FolderPicker';

const styles = {
  zone: {
    border: '2px dashed #3f3f46', borderRadius: 16, padding: '50px 40px',
    textAlign: 'center', cursor: 'pointer', background: '#18181b',
  },
  zoneActive: { borderColor: '#a78bfa', background: '#1e1b2e' },
  icon: { fontSize: 48, marginBottom: 16 },
  title: { fontSize: 18, fontWeight: 600, marginBottom: 8 },
  hint: { color: '#71717a', fontSize: 14 },
  btn: {
    marginTop: 20, padding: '10px 32px', background: '#7c3aed', color: '#fff',
    border: 'none', borderRadius: 8, fontSize: 16, cursor: 'pointer', fontWeight: 600,
  },
  btnDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  divider: {
    display: 'flex', alignItems: 'center', gap: 16, margin: '20px 0',
    color: '#52525b', fontSize: 13,
  },
  dividerLine: { flex: 1, height: 1, background: '#27272a' },
  folderSection: {
    background: '#18181b', borderRadius: 12, padding: 24, marginBottom: 20,
    border: '1px solid #27272a',
  },
  folderRow: { display: 'flex', gap: 12, alignItems: 'center' },
  folderInput: {
    flex: 1, background: '#27272a', border: '1px solid #3f3f46', borderRadius: 8,
    padding: '10px 14px', color: '#e4e4e7', fontSize: 14, outline: 'none',
  },
  browseBtn: {
    padding: '10px 16px', background: '#3f3f46', color: '#e4e4e7', border: 'none',
    borderRadius: 8, fontSize: 14, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  scanBtn: {
    padding: '10px 24px', background: '#2563eb', color: '#fff', border: 'none',
    borderRadius: 8, fontSize: 14, cursor: 'pointer', fontWeight: 600, whiteSpace: 'nowrap',
  },
  topBar: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8,
  },
  actionBtn: {
    padding: '6px 14px', background: '#27272a', color: '#a1a1aa',
    border: '1px solid #3f3f46', borderRadius: 6, fontSize: 12, cursor: 'pointer',
  },
};

export default function UploadZone({ onUpload, onScanFolder, onClearCache, onShowHistory, loading }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [folderPath, setFolderPath] = useState('');
  const [showPicker, setShowPicker] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false);
    setFiles(Array.from(e.dataTransfer.files).filter(f =>
      /\.(jpg|jpeg|png|bmp|tiff|webp|heic|heif)$/i.test(f.name)));
  };

  const handleFolderPicked = (path) => {
    setFolderPath(path);
    setShowPicker(false);
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Top action buttons */}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginBottom: 16 }}>
        {onShowHistory && (
          <button style={styles.actionBtn} onClick={onShowHistory}>历史记录</button>
        )}
        {onClearCache && (
          <button style={styles.actionBtn} onClick={onClearCache}>清理缓存</button>
        )}
      </div>

      {/* Folder scan section */}
      <div style={styles.folderSection}>
        <div style={{ ...styles.title, marginBottom: 12, textAlign: 'left' }}>从文件夹扫描</div>
        <div style={styles.folderRow}>
          <input
            type="text" placeholder="输入或选择照片文件夹路径..."
            value={folderPath} onChange={e => setFolderPath(e.target.value)}
            style={styles.folderInput}
            onKeyDown={e => e.key === 'Enter' && folderPath.trim() && onScanFolder(folderPath.trim())}
          />
          <button style={styles.browseBtn} onClick={() => setShowPicker(true)}>浏览...</button>
          <button
            style={{ ...styles.scanBtn, ...(loading ? styles.btnDisabled : {}) }}
            disabled={loading || !folderPath.trim()}
            onClick={() => onScanFolder(folderPath.trim())}
          >
            {loading ? '扫描中...' : '开始扫描'}
          </button>
        </div>
        <div style={{ ...styles.hint, marginTop: 8, textAlign: 'left' }}>
          直接读取文件夹中的照片，无需复制，不占额外空间
        </div>
      </div>

      {/* Divider */}
      <div style={styles.divider}>
        <div style={styles.dividerLine} /><span>或</span><div style={styles.dividerLine} />
      </div>

      {/* Upload section */}
      <div
        style={{ ...styles.zone, ...(dragging ? styles.zoneActive : {}) }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" multiple accept="image/*"
          style={{ display: 'none' }} onChange={e => setFiles(Array.from(e.target.files))} />
        <div style={styles.icon}>{dragging ? '📥' : '📷'}</div>
        <div style={styles.title}>
          {files.length > 0 ? `已选择 ${files.length} 张照片` : '拖拽照片到这里，或点击选择'}
        </div>
        <div style={styles.hint}>支持 JPG / PNG / BMP / TIFF / WebP / HEIC</div>
        {files.length > 0 && (
          <button
            style={{ ...styles.btn, ...(loading ? styles.btnDisabled : {}) }}
            disabled={loading}
            onClick={e => { e.stopPropagation(); onUpload(files); }}
          >
            {loading ? '提交中...' : `开始分析 ${files.length} 张照片`}
          </button>
        )}
      </div>

      {/* Folder picker modal */}
      {showPicker && (
        <FolderPicker onSelect={handleFolderPicked} onClose={() => setShowPicker(false)} />
      )}
    </div>
  );
}
