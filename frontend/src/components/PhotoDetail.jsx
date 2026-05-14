import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { thumbnailUrl } from '../api';

const gradeColors = { S: '#a855f7', A: '#22c55e', 'B+': '#3b82f6', B: '#06b6d4', 'C+': '#eab308', C: '#f97316', D: '#ef4444' };

export default function PhotoDetail({ photo, taskId, onClose }) {
  const nima = photo.aesthetic?.nima_score || photo.aesthetic?.overall;
  return (
    <div style={s.overlay} onClick={onClose}>
      <div style={s.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={s.header}>
          <div style={s.filename}>{photo.filename}</div>
          <button style={s.closeBtn} onClick={onClose}>×</button>
        </div>

        {/* Top: thumbnail left + score/radar right */}
        <div style={s.topRow}>
          <div style={s.thumbCol}>
            <img src={thumbnailUrl(taskId, photo.filename)} alt={photo.filename} style={s.img} />
            {photo.exif && (photo.exif.camera_model || photo.exif.lens_model) && (
              <div style={s.exifBox}>
                {photo.exif.camera_model && (
                  <div style={s.exifLine}>
                    <span style={s.exifKey}>相机</span>
                    <span style={s.exifVal}>{[photo.exif.camera_make, photo.exif.camera_model].filter(Boolean).join(' ')}</span>
                  </div>
                )}
                {photo.exif.lens_model && (
                  <div style={s.exifLine}>
                    <span style={s.exifKey}>镜头</span>
                    <span style={s.exifVal}>{photo.exif.lens_model}</span>
                  </div>
                )}
                {(photo.exif.aperture || photo.exif.shutter_speed || photo.exif.iso) && (
                  <div style={s.exifLine}>
                    <span style={s.exifKey}>参数</span>
                    <span style={s.exifVal}>
                      {[photo.exif.focal_length, photo.exif.aperture, photo.exif.shutter_speed, photo.exif.iso && `ISO${photo.exif.iso}`].filter(Boolean).join('  ·  ')}
                    </span>
                  </div>
                )}
                {photo.exif.datetime_original && (
                  <div style={s.exifLine}>
                    <span style={s.exifKey}>时间</span>
                    <span style={s.exifVal}>{photo.exif.datetime_original}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div style={s.scoreRadarCol}>
            {/* Score badge */}
            <div style={s.scoreBox}>
              <span style={{ ...s.bigScore, color: gradeColors[photo.grade] }}>{photo.final_score}</span>
              <span style={{ ...s.grade, background: gradeColors[photo.grade] }}>{photo.grade}</span>
            </div>
            {/* Radar */}
            <div style={s.radarWrap}>
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData(photo)}>
                  <PolarGrid stroke="#3f3f46" />
                  <PolarAngleAxis dataKey="axis" tick={{ fill: '#a1a1aa', fontSize: 10 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} />
                  <Radar dataKey="value" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.25} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Bottom: detail grid */}
        <div style={s.grid}>
          <Section title="技术质量">
            <Row l="曝光" v={photo.technical?.exposure} />
            <Row l="锐度" v={photo.technical?.sharpness} />
            <Row l="色彩" v={photo.technical?.color} />
            <Row l="噪点" v={photo.technical?.noise} />
            <Row l="动态范围" v={photo.technical?.dynamic_range} />
            <Row l="对焦质量" v={photo.technical?.focus_quality} />
            <Row l="色彩丰富度" v={photo.technical?.color_richness} />
          </Section>

          <Section title="构图分析">
            <Row l="三分法" v={photo.composition?.rule_of_thirds} />
            <Row l="对称性" v={photo.composition?.symmetry} />
            <Row l="水平线" v={photo.composition?.horizon_level} />
            <Row l="留白" v={photo.composition?.negative_space} />
            <Row l="引导线" v={photo.composition?.leading_lines} />
            <Row l="景深" v={photo.composition?.depth_of_field} />
          </Section>

          <Section title={`美学评分${photo.aesthetic?.method === 'nima' ? ' (NIMA)' : ''}`}>
            <Row l="美学得分" v={nima} />
            <Row l="对比度" v={photo.aesthetic?.contrast} />
            <Row l="色彩和谐" v={photo.aesthetic?.color_harmony} />
          </Section>

          <Section title="拍摄参数">
            <Row l="光圈" v={photo.exif?.aperture || '-'} raw />
            <Row l="快门" v={photo.exif?.shutter_speed || '-'} raw />
            <Row l="ISO" v={photo.exif?.iso || '-'} raw />
            <Row l="焦距" v={photo.exif?.focal_length || '-'} raw />
            {photo.exif?.focal_length_35mm && <Row l="等效焦距" v={photo.exif.focal_length_35mm} raw />}
            {photo.exif?.exposure_comp && <Row l="曝光补偿" v={photo.exif.exposure_comp} raw />}
            {photo.exif?.exposure_program && <Row l="拍摄模式" v={photo.exif.exposure_program} raw />}
            {photo.exif?.metering_mode && <Row l="测光" v={photo.exif.metering_mode} raw />}
            {photo.exif?.white_balance && <Row l="白平衡" v={photo.exif.white_balance} raw />}
            {photo.exif?.flash && <Row l="闪光灯" v={photo.exif.flash} raw />}
            {photo.exif?.image_size && <Row l="分辨率" v={photo.exif.image_size} raw />}
            {photo.exif?.color_space && <Row l="色彩空间" v={photo.exif.color_space} raw />}
          </Section>

          <Section title="场景语义" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
              <Row l="场景" v={photo.semantic?.scene} raw />
              <Row l="氛围" v={photo.semantic?.mood} raw />
              {photo.semantic?.tags?.length > 0 && (
                <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                  {photo.semantic.tags.map((t) => <span key={t} style={s.tag}>{t}</span>)}
                </div>
              )}
            </div>
          </Section>

          {photo.suggestions && (
            <div style={{ gridColumn: '1 / -1', ...s.card, background: '#161618' }}>
              <div style={s.cardTitle}>评价与建议</div>
              <div style={{ fontSize: 13, color: '#d4d4d8', lineHeight: 1.7, whiteSpace: 'pre-line' }}>
                {photo.suggestions}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---- sub-components ---- */

function Section({ title, children, style }) {
  return (
    <div style={{ ...s.card, ...style }}>
      <div style={s.cardTitle}>{title}</div>
      {children}
    </div>
  );
}

function Row({ l, v, raw }) {
  if (v === undefined || v === null) return null;
  if (raw) {
    return (
      <div style={s.row}>
        <span style={s.rowL}>{l}</span>
        <span style={s.rowV}>{v}</span>
      </div>
    );
  }
  const pct = Math.min(100, v);
  const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#eab308' : '#ef4444';
  return (
    <div style={s.row}>
      <span style={s.rowL}>{l}</span>
      <span style={{ ...s.rowV, color }}>{typeof v === 'number' ? v.toFixed(1) : v}</span>
    </div>
  );
}

/* ---- data ---- */

const radarData = (p) => [
  { axis: '曝光', value: p.technical?.exposure || 0 },
  { axis: '锐度', value: p.technical?.sharpness || 0 },
  { axis: '色彩', value: p.technical?.color || 0 },
  { axis: '噪点', value: p.technical?.noise || 0 },
  { axis: '动态范围', value: p.technical?.dynamic_range || 0 },
  { axis: '对焦', value: p.technical?.focus_quality || 0 },
  { axis: '构图', value: p.composition?.overall || 0 },
  { axis: '美学', value: p.aesthetic?.nima_score || p.aesthetic?.overall || 0 },
  { axis: '色彩丰富', value: p.technical?.color_richness || 0 },
  { axis: '语义', value: p.semantic?.overall || 0 },
];

/* ---- styles ---- */

const s = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 100 },
  modal: { background: '#18181b', borderRadius: 14, width: '94%', maxWidth: 1100, maxHeight: '92vh', overflow: 'auto', padding: '20px 24px', border: '1px solid #27272a' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  filename: { fontSize: 16, fontWeight: 600, color: '#e4e4e7', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  closeBtn: { background: 'none', border: 'none', color: '#71717a', fontSize: 22, cursor: 'pointer', padding: '0 6px', flexShrink: 0 },

  // top row: thumb + score/radar
  topRow: { display: 'flex', gap: 20, marginBottom: 16, flexWrap: 'wrap' },
  thumbCol: { flex: '1 1 280px', maxWidth: 420 },
  img: { width: '100%', borderRadius: 10, maxHeight: 340, objectFit: 'contain', background: '#27272a', display: 'block' },
  exifBox: { marginTop: 8, padding: '8px 12px', background: '#1e1e22', borderRadius: 8, fontSize: 12, display: 'flex', flexDirection: 'column', gap: 3 },
  exifLine: { display: 'flex', gap: 6 },
  exifKey: { color: '#71717a', minWidth: 36, flexShrink: 0 },
  exifVal: { color: '#d4d4d8', fontWeight: 500 },
  scoreRadarCol: { flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: 8 },
  scoreBox: { display: 'flex', alignItems: 'center', gap: 10 },
  bigScore: { fontSize: 44, fontWeight: 800, lineHeight: 1 },
  grade: { display: 'inline-block', padding: '3px 14px', borderRadius: 7, fontSize: 16, fontWeight: 700, color: '#fff' },
  radarWrap: { background: '#1e1e22', borderRadius: 10, padding: '8px 0' },

  // detail grid
  grid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 },
  card: { background: '#1e1e22', borderRadius: 10, padding: '10px 14px' },
  cardTitle: { fontSize: 11, fontWeight: 600, color: '#a78bfa', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 },
  row: { display: 'flex', justifyContent: 'space-between', padding: '2px 0', fontSize: 12 },
  rowL: { color: '#a1a1aa' },
  rowV: { fontWeight: 600 },
  tag: { background: '#27272a', padding: '2px 9px', borderRadius: 10, fontSize: 11, color: '#a1a1aa' },
};
