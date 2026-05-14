import React, { useRef, useCallback } from 'react';

const styles = {
  bar: {
    display: 'flex',
    gap: 16,
    alignItems: 'center',
    padding: '16px 0',
    flexWrap: 'wrap',
  },
  group: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  label: {
    fontSize: 13,
    color: '#a1a1aa',
    whiteSpace: 'nowrap',
  },
  input: {
    background: '#27272a',
    border: '1px solid #3f3f46',
    borderRadius: 6,
    padding: '5px 10px',
    color: '#e4e4e7',
    fontSize: 13,
    width: 70,
  },
  select: {
    background: '#27272a',
    border: '1px solid #3f3f46',
    borderRadius: 6,
    padding: '5px 10px',
    color: '#e4e4e7',
    fontSize: 13,
  },
};

function FilterBar({ filters, onChange }) {
  const timerRef = useRef(null);

  const debouncedChange = useCallback((newFilters) => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onChange(newFilters), 300);
  }, [onChange]);

  return (
    <div style={styles.bar}>
      <div style={styles.group}>
        <span style={styles.label}>最低分:</span>
        <input
          type="number"
          min={0}
          max={100}
          value={filters.minScore}
          style={styles.input}
          onChange={(e) => {
            const newFilters = { ...filters, minScore: Number(e.target.value) };
            debouncedChange(newFilters);
          }}
        />
      </div>
      <div style={styles.group}>
        <span style={styles.label}>等级:</span>
        <select
          value={filters.grade}
          style={styles.select}
          onChange={(e) => onChange({ ...filters, grade: e.target.value })}
        >
          <option value="">全部</option>
          <option value="S">S - 顶级</option>
          <option value="A">A - 优秀</option>
          <option value="B+">B+ - 良好</option>
          <option value="B">B - 中上</option>
          <option value="C+">C+ - 中等</option>
          <option value="C">C - 一般</option>
          <option value="D">D - 不推荐</option>
        </select>
      </div>
      <div style={styles.group}>
        <span style={styles.label}>排序:</span>
        <select
          value={filters.sortBy}
          style={styles.select}
          onChange={(e) => onChange({ ...filters, sortBy: e.target.value })}
        >
          <option value="final_score">按评分</option>
          <option value="filename">按文件名</option>
        </select>
      </div>
    </div>
  );
}

export default React.memo(FilterBar, (prev, next) => {
  return prev.filters === next.filters && prev.onChange === next.onChange;
});
