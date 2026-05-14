import React, { useState, useRef, useCallback, useEffect } from 'react';
import UploadZone from './components/UploadZone';
import TaskList from './components/TaskList';
import ProgressBar from './components/ProgressBar';
import PhotoGrid from './components/PhotoGrid';
import FilterBar from './components/FilterBar';
import PhotoDetail from './components/PhotoDetail';
import HistoryPanel from './components/HistoryPanel';
import { uploadPhotos, scanFolder, getTaskStatus, getResults, clearCache, deletePhotos } from './api';

const DEFAULT_FILTERS = { minScore: 0, grade: '', sortBy: 'final_score', limit: 100, offset: 0 };

export default function App() {
  // tasks: Map<taskId, { status, results, folderName, pollRef, filters }>
  const [tasks, setTasks] = useState(new Map());
  // { type: 'list' } | { type: 'task', taskId }
  const [activeView, setActiveView] = useState({ type: 'list' });
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  // Ref to access tasks Map in cleanup (avoids stale closure)
  const tasksRef = useRef(tasks);
  useEffect(() => { tasksRef.current = tasks; }, [tasks]);

  // Cleanup all polling on unmount
  useEffect(() => {
    return () => {
      for (const [, task] of tasksRef.current) {
        if (task.pollRef) clearInterval(task.pollRef);
      }
    };
  }, []);

  const stopPollingFor = useCallback((tid) => {
    setTasks(prev => {
      const task = prev.get(tid);
      if (!task) return prev;
      if (task.pollRef) clearInterval(task.pollRef);
      const next = new Map(prev);
      next.set(tid, { ...task, pollRef: null });
      return next;
    });
  }, []);

  const loadResults = useCallback(async (tid) => {
    try {
      // Read current filters from the task entry
      let filters = DEFAULT_FILTERS;
      setTasks(prev => {
        const task = prev.get(tid);
        if (task) filters = task.filters || DEFAULT_FILTERS;
        return prev; // no change yet
      });
      const data = await getResults(tid, filters);
      setTasks(prev => {
        const task = prev.get(tid);
        if (!task) return prev;
        const next = new Map(prev);
        next.set(tid, { ...task, results: data });
        return next;
      });
    } catch (e) {
      console.error('Failed to load results:', e);
    }
  }, []);

  const startTask = useCallback((tid, initialStatus, folderName) => {
    // Create the polling interval
    const interval = setInterval(async () => {
      try {
        const s = await getTaskStatus(tid);
        setTasks(prev => {
          const task = prev.get(tid);
          if (!task) { clearInterval(interval); return prev; }
          const next = new Map(prev);
          if (s.status === 'completed') {
            clearInterval(interval);
            next.set(tid, { ...task, status: s, pollRef: null });
            // Trigger result loading outside setState
            setTimeout(() => loadResults(tid), 0);
          } else if (s.status === 'failed') {
            clearInterval(interval);
            next.set(tid, { ...task, status: s, pollRef: null });
          } else {
            next.set(tid, { ...task, status: s });
          }
          return next;
        });
      } catch (e) { /* ignore transient network errors */ }
    }, 1500);

    // Add task to the Map
    setTasks(prev => {
      // Stop existing polling if task already exists
      const existing = prev.get(tid);
      if (existing?.pollRef) clearInterval(existing.pollRef);
      const next = new Map(prev);
      next.set(tid, {
        status: initialStatus || { status: 'pending', total: 0, processed: 0, current_file: '' },
        results: null,
        folderName: folderName || tid,
        pollRef: interval,
        filters: { ...DEFAULT_FILTERS },
      });
      return next;
    });
  }, [loadResults]);

  const handleUpload = async (files) => {
    setLoading(true);
    try {
      const data = await uploadPhotos(files);
      if (data.error) { alert(data.error); return; }
      startTask(data.task_id, { status: 'pending', total: data.file_count, processed: 0, current_file: '等待开始...' }, '上传照片');
    } catch (e) { alert('上传失败: ' + e.message); }
    finally { setLoading(false); }
  };

  const handleScanFolder = async (folderPath) => {
    setLoading(true);
    try {
      const data = await scanFolder(folderPath);
      if (data.error) { alert(data.error); return; }
      startTask(data.task_id, { status: 'pending', total: data.file_count, processed: 0, current_file: '等待开始...' }, folderPath);
    } catch (e) { alert('扫描失败: ' + e.message); }
    finally { setLoading(false); }
  };

  const handleClearCache = async () => {
    if (!confirm('确认清理所有缓存数据？将删除已完成的分析结果和缩略图，正在进行的任务不受影响。')) return;
    try {
      const data = await clearCache();
      if (data.warnings?.length > 0) {
        alert('缓存已部分清理:\n' + data.warnings.join('\n'));
      } else {
        alert('缓存已清理');
      }
      // Only remove completed/failed tasks, keep running tasks alive
      setTasks(prev => {
        const next = new Map();
        for (const [tid, task] of prev) {
          const st = task.status?.status;
          if (st === 'processing' || st === 'pending') {
            // Keep running tasks
            next.set(tid, task);
          } else {
            // Stop polling and discard completed/failed tasks
            if (task.pollRef) clearInterval(task.pollRef);
          }
        }
        return next;
      });
      // If active view was a removed task, switch to list
      setActiveView(prev => {
        if (prev.type === 'task') {
          // Check if task still exists after state update via a ref-like approach
          // We'll just switch to list if the active task might have been cleared
          return { type: 'list' };
        }
        return prev;
      });
      setSelected(null);
    } catch (e) { alert('清理失败: ' + e.message); }
  };

  const handleDelete = async (ids) => {
    if (!confirm(`确认删除 ${ids.length} 张照片？将同时删除源文件和分析记录。`)) return;
    try {
      const data = await deletePhotos(ids, true);
      if (data.errors?.length > 0) {
        alert(`删除完成，${data.errors.length} 个文件删除失败`);
      }
      if (activeView.type === 'task') loadResults(activeView.taskId);
    } catch (e) { alert('删除失败: ' + e.message); }
  };

  const handleFilterChange = useCallback((taskId, newFilters) => {
    // Reset to first page when filters change
    const filtersWithReset = { ...newFilters, offset: 0 };
    setTasks(prev => {
      const task = prev.get(taskId);
      if (!task) return prev;
      const next = new Map(prev);
      next.set(taskId, { ...task, filters: filtersWithReset });
      return next;
    });
    (async () => {
      try {
        const data = await getResults(taskId, filtersWithReset);
        setTasks(prev => {
          const task = prev.get(taskId);
          if (!task) return prev;
          const next = new Map(prev);
          next.set(taskId, { ...task, results: data });
          return next;
        });
      } catch (e) { console.error(e); }
    })();
  }, []);

  const handlePageChange = useCallback((taskId, newOffset) => {
    let newFilters;
    setTasks(prev => {
      const task = prev.get(taskId);
      if (!task) return prev;
      newFilters = { ...task.filters, offset: newOffset };
      const next = new Map(prev);
      next.set(taskId, { ...task, filters: newFilters });
      return next;
    });
    if (!newFilters) return;
    (async () => {
      try {
        const data = await getResults(taskId, newFilters);
        setTasks(prev => {
          const task = prev.get(taskId);
          if (!task) return prev;
          const next = new Map(prev);
          next.set(taskId, { ...task, results: data });
          return next;
        });
      } catch (e) { console.error(e); }
    })();
  }, []);

  const handleSelectTask = useCallback((tid) => {
    setActiveView({ type: 'task', taskId: tid });
    setSelected(null);
  }, []);

  const handleRemoveTask = useCallback((tid) => {
    if (!confirm('确认移除此任务？')) return;
    setTasks(prev => {
      const task = prev.get(tid);
      if (!task) return prev;
      if (task.pollRef) clearInterval(task.pollRef);
      const next = new Map(prev);
      next.delete(tid);
      return next;
    });
  }, []);

  const handleHistorySelect = useCallback(async (tid) => {
    setShowHistory(false);
    // If task already in Map, just switch to it
    if (tasks.has(tid)) {
      setActiveView({ type: 'task', taskId: tid });
      return;
    }
    // Otherwise load results from history (no polling)
    try {
      const data = await getResults(tid, DEFAULT_FILTERS);
      setTasks(prev => {
        const next = new Map(prev);
        next.set(tid, {
          status: { status: 'completed', total: data.count, processed: data.count, current_file: '' },
          results: data,
          folderName: `历史记录 ${tid}`,
          pollRef: null,
          filters: { ...DEFAULT_FILTERS },
        });
        return next;
      });
      setActiveView({ type: 'task', taskId: tid });
    } catch (e) { alert('加载历史记录失败: ' + e.message); }
  }, [tasks]);

  // Get current active task data
  const activeTask = activeView.type === 'task' ? tasks.get(activeView.taskId) : null;
  const activeTaskId = activeView.type === 'task' ? activeView.taskId : null;

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: 24 }}>
      <header style={{ marginBottom: 32, textAlign: 'center' }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: '#a78bfa' }}>PhotoAutoPick</h1>
        <p style={{ color: '#71717a', marginTop: 8 }}>
          AI 照片自动筛选 — 构图 · 曝光 · 美学 · 语义
        </p>
      </header>

      {/* UploadZone always visible */}
      <UploadZone
        onUpload={handleUpload}
        onScanFolder={handleScanFolder}
        onClearCache={handleClearCache}
        onShowHistory={() => setShowHistory(true)}
        loading={loading}
      />

      {/* Task list always visible when tasks exist */}
      {tasks.size > 0 && (
        <TaskList
          tasks={tasks}
          activeTaskId={activeView.type === 'task' ? activeView.taskId : null}
          onSelectTask={handleSelectTask}
          onRemoveTask={handleRemoveTask}
        />
      )}

      {/* Active task detail view (progress + results) */}
      {activeView.type === 'task' && activeTask && (
        <>
          {/* Progress bar for running tasks */}
          {activeTask.status && activeTask.status.status !== 'completed' && (
            <ProgressBar status={activeTask.status} />
          )}

          {/* Results */}
          {activeTask.results && (
            <>
              <FilterBar
                filters={activeTask.filters}
                onChange={(f) => handleFilterChange(activeTaskId, f)}
              />
              <PhotoGrid
                results={activeTask.results.results}
                taskId={activeTaskId}
                onSelect={setSelected}
                onDelete={handleDelete}
              />
              {/* Pagination */}
              {activeTask.results.count > (activeTask.filters.limit || 100) && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 16, padding: '12px 0' }}>
                  <button
                    disabled={(activeTask.filters.offset || 0) === 0}
                    onClick={() => handlePageChange(activeTaskId, Math.max(0, (activeTask.filters.offset || 0) - (activeTask.filters.limit || 100)))}
                    style={{
                      padding: '6px 16px', background: (activeTask.filters.offset || 0) === 0 ? '#27272a' : '#3f3f46',
                      color: (activeTask.filters.offset || 0) === 0 ? '#52525b' : '#e4e4e7',
                      border: '1px solid #3f3f46', borderRadius: 6, fontSize: 13,
                      cursor: (activeTask.filters.offset || 0) === 0 ? 'not-allowed' : 'pointer',
                    }}
                  >
                    上一页
                  </button>
                  <span style={{ color: '#a1a1aa', fontSize: 13 }}>
                    {Math.floor((activeTask.filters.offset || 0) / (activeTask.filters.limit || 100)) + 1}
                    {' / '}
                    {Math.ceil(activeTask.results.count / (activeTask.filters.limit || 100))}
                    {' 页'}
                    <span style={{ marginLeft: 8, color: '#71717a' }}>
                      (共 {activeTask.results.count} 张)
                    </span>
                  </span>
                  <button
                    disabled={(activeTask.filters.offset || 0) + (activeTask.filters.limit || 100) >= activeTask.results.count}
                    onClick={() => handlePageChange(activeTaskId, (activeTask.filters.offset || 0) + (activeTask.filters.limit || 100))}
                    style={{
                      padding: '6px 16px',
                      background: (activeTask.filters.offset || 0) + (activeTask.filters.limit || 100) >= activeTask.results.count ? '#27272a' : '#3f3f46',
                      color: (activeTask.filters.offset || 0) + (activeTask.filters.limit || 100) >= activeTask.results.count ? '#52525b' : '#e4e4e7',
                      border: '1px solid #3f3f46', borderRadius: 6, fontSize: 13,
                      cursor: (activeTask.filters.offset || 0) + (activeTask.filters.limit || 100) >= activeTask.results.count ? 'not-allowed' : 'pointer',
                    }}
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {selected && (
        <PhotoDetail
          photo={selected}
          taskId={activeTaskId}
          onClose={() => setSelected(null)}
        />
      )}

      {showHistory && (
        <HistoryPanel
          onSelect={handleHistorySelect}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  );
}
