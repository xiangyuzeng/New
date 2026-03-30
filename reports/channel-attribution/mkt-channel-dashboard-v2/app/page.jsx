'use client';

import { useState } from 'react';
import {
  ComposedChart, BarChart, Bar, Line, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';
import { monthlyData, grandTotals, latestMonth, prevMonth, momChange, COLORS, methodology } from './data';

const fmt = (n) => n.toLocaleString('en-US');
const pct = (n) => `${n.toFixed(1)}%`;

// ── Styles ──
const s = {
  header: {
    background: 'linear-gradient(135deg, #0365C0 0%, #1A365D 100%)',
    color: '#fff', padding: '28px 40px', marginBottom: 24,
  },
  headerTitle: { fontSize: 26, fontWeight: 700, margin: 0, letterSpacing: 0.5 },
  headerSub: { fontSize: 14, opacity: 0.85, marginTop: 6 },
  container: { maxWidth: 1280, margin: '0 auto', padding: '0 24px 48px' },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 18, fontWeight: 700, color: '#1A365D', marginBottom: 16 },
  card: {
    background: '#fff', borderRadius: 12, padding: '24px 28px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
  },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 },
  kpiLabel: { fontSize: 13, color: '#6b7280', marginBottom: 6, fontFamily: 'var(--font-cn)' },
  kpiValue: { fontSize: 32, fontWeight: 700, fontFamily: 'var(--font-mono)', margin: 0 },
  kpiSub: { fontSize: 12, color: '#6b7280', marginTop: 4 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    padding: '10px 12px', textAlign: 'left', borderBottom: '2px solid #e5e7eb',
    fontSize: 12, fontWeight: 600, color: '#6b7280', whiteSpace: 'nowrap',
  },
  td: { padding: '10px 12px', borderBottom: '1px solid #f3f4f6' },
  mono: { fontFamily: 'var(--font-mono)' },
  badge: (color) => ({
    display: 'inline-block', padding: '2px 8px', borderRadius: 6,
    fontSize: 12, fontWeight: 600, background: color + '18', color,
  }),
  collapsible: { cursor: 'pointer', userSelect: 'none', display: 'flex', alignItems: 'center', gap: 8 },
  recCard: {
    background: '#fff', borderRadius: 10, padding: '16px 20px', border: '1px solid #e5e7eb',
  },
};

// ── KPI Card ──
function KPICard({ label, value, sub, color }) {
  return (
    <div style={s.card}>
      <div style={s.kpiLabel}>{label}</div>
      <p style={{ ...s.kpiValue, color: color || '#1A365D' }}>{value}</p>
      {sub && <div style={s.kpiSub}>{sub}</div>}
    </div>
  );
}

// ── Custom Tooltip for Trend Chart ──
function TrendTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '12px 16px', fontSize: 13, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
      <div style={{ fontWeight: 600, marginBottom: 8, color: '#1A365D' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 2 }}>
          <span style={{ color: p.color }}>{p.name}</span>
          <span style={{ ...s.mono, fontWeight: 600 }}>
            {p.name.includes('%') ? `${p.value}%` : fmt(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Stacked Tooltip ──
function StackedTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const total = payload.reduce((sum, p) => sum + p.value, 0);
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '12px 16px', fontSize: 13, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
      <div style={{ fontWeight: 600, marginBottom: 8, color: '#1A365D' }}>{label}  ({fmt(total)} total)</div>
      {payload.reverse().map((p, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 2 }}>
          <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: p.color, marginRight: 6 }} />{p.name}</span>
          <span style={s.mono}>{fmt(p.value)} ({(p.value / total * 100).toFixed(1)}%)</span>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [methodOpen, setMethodOpen] = useState(false);

  const trendData = monthlyData.map((d) => ({
    name: d.label,
    'Marketing %': d.marketingPct,
    'Marketing Users': d.marketingTotal,
    'Total Registrations': d.total,
  }));

  const stackedData = monthlyData.map((d) => ({
    name: d.label,
    'iOS Organic': d.ios,
    'Android Organic': d.android,
    'QR Scan (est.)': d.qrScan,
    'Referral': d.referral,
    'Google Maps (est.)': d.googleMaps,
    'Social/Other': d.socialOther,
  }));

  const arrow = momChange >= 0 ? '\u2191' : '\u2193';
  const momColor = momChange >= 0 ? COLORS.up : COLORS.down;

  return (
    <div>
      {/* ── Header ── */}
      <header style={s.header}>
        <h1 style={s.headerTitle}>瑞幸北美 &middot; 渠道流量贡献分析 V2</h1>
        <div style={s.headerSub}>基于排除法的营销团队贡献度追踪 &nbsp;|&nbsp; LCNA-MKT-2026-004 &nbsp;|&nbsp; {latestMonth.month} data</div>
      </header>

      <div style={s.container}>
        {/* ── Section 1: KPI Cards ── */}
        <div style={{ ...s.section, ...s.kpiGrid }}>
          <KPICard
            label="总注册量 (Latest Month)"
            value={fmt(latestMonth.total)}
            sub={`${latestMonth.label} | Grand total: ${fmt(grandTotals.total)}`}
            color="#1A365D"
          />
          <KPICard
            label="营销贡献占比"
            value={pct(latestMonth.marketingPct)}
            sub={`${fmt(latestMonth.marketingTotal)} marketing-attributable users`}
            color="#0365C0"
          />
          <KPICard
            label="自然/门店渠道占比"
            value={pct(latestMonth.organicPct)}
            sub={`iOS + Android organic + QR scan`}
            color="#00A5A5"
          />
          <KPICard
            label="月环比变化 (MoM)"
            value={`${arrow} ${momChange > 0 ? '+' : ''}${momChange}pp`}
            sub={`${prevMonth.label}: ${pct(prevMonth.marketingPct)} → ${latestMonth.label}: ${pct(latestMonth.marketingPct)}`}
            color={momColor}
          />
        </div>

        {/* ── Section 2: Monthly Trend Chart ── */}
        <div style={s.section}>
          <h2 style={s.sectionTitle}>月度营销贡献趋势 Monthly Marketing Contribution Trend</h2>
          <div style={s.card}>
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis
                  yAxisId="pct" orientation="left" domain={[0, 30]}
                  tick={{ fontSize: 12 }} label={{ value: 'Marketing %', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 12, fill: '#6b7280' } }}
                  tickFormatter={(v) => `${v}%`}
                />
                <YAxis
                  yAxisId="count" orientation="right" domain={[0, 30000]}
                  tick={{ fontSize: 12 }} label={{ value: 'Users', angle: 90, position: 'insideRight', offset: 10, style: { fontSize: 12, fill: '#6b7280' } }}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<TrendTooltip />} />
                <Legend wrapperStyle={{ fontSize: 13 }} />
                <Area
                  yAxisId="count" type="monotone" dataKey="Total Registrations"
                  fill="#e0e7ff" stroke="#a5b4fc" fillOpacity={0.3} strokeWidth={1.5}
                />
                <Bar
                  yAxisId="count" dataKey="Marketing Users"
                  fill={COLORS.primary} radius={[4, 4, 0, 0]} barSize={32} fillOpacity={0.8}
                />
                <Line
                  yAxisId="pct" type="monotone" dataKey="Marketing %"
                  stroke="#EF4444" strokeWidth={3} dot={{ r: 5, fill: '#EF4444' }}
                  activeDot={{ r: 7 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 8, textAlign: 'center' }}>
              Red line = Marketing % (left axis) &nbsp;|&nbsp; Blue bars = Marketing users (right axis) &nbsp;|&nbsp; Shaded area = Total registrations (right axis)
            </div>
          </div>
        </div>

        {/* ── Section 3: Monthly Breakdown Table ── */}
        <div style={s.section}>
          <h2 style={s.sectionTitle}>月度渠道贡献明细 Monthly Channel Breakdown</h2>
          <div style={{ ...s.card, overflowX: 'auto' }}>
            <table style={s.table}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={s.th}>Month</th>
                  <th style={{ ...s.th, textAlign: 'right' }}>Total</th>
                  <th style={{ ...s.th, textAlign: 'right', color: COLORS.iosOrganic }}>iOS Organic</th>
                  <th style={{ ...s.th, textAlign: 'right', color: COLORS.androidOrganic }}>Android</th>
                  <th style={{ ...s.th, textAlign: 'right', color: COLORS.qrScan }}>QR Scan*</th>
                  <th style={{ ...s.th, textAlign: 'right', borderLeft: '2px solid #e5e7eb' }}>Organic Sub</th>
                  <th style={{ ...s.th, textAlign: 'right', color: COLORS.referral }}>Referral</th>
                  <th style={{ ...s.th, textAlign: 'right', color: COLORS.googleMaps }}>Google Maps*</th>
                  <th style={{ ...s.th, textAlign: 'right', color: COLORS.socialOther }}>Social/Other</th>
                  <th style={{ ...s.th, textAlign: 'right', borderLeft: '2px solid #e5e7eb' }}>Mkt Sub</th>
                  <th style={{ ...s.th, textAlign: 'center' }}>Marketing %</th>
                  <th style={{ ...s.th, textAlign: 'center' }}>MoM</th>
                </tr>
              </thead>
              <tbody>
                {monthlyData.map((d, i) => {
                  const prev = i > 0 ? monthlyData[i - 1].marketingPct : null;
                  const diff = prev !== null ? +(d.marketingPct - prev).toFixed(1) : null;
                  const diffColor = diff === null ? '#6b7280' : diff >= 0 ? COLORS.up : COLORS.down;
                  return (
                    <tr key={d.month} style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb' }}>
                      <td style={{ ...s.td, fontWeight: 600 }}>{d.label}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right', fontWeight: 600 }}>{fmt(d.total)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(d.ios)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(d.android)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(d.qrScan)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right', fontWeight: 600, borderLeft: '2px solid #f3f4f6' }}>{fmt(d.organicTotal)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(d.referral)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(d.googleMaps)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(d.socialOther)}</td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'right', fontWeight: 600, borderLeft: '2px solid #f3f4f6' }}>{fmt(d.marketingTotal)}</td>
                      <td style={{ ...s.td, textAlign: 'center' }}>
                        <span style={s.badge(d.marketingPct >= (prev || 0) ? COLORS.up : COLORS.down)}>
                          {pct(d.marketingPct)}
                        </span>
                      </td>
                      <td style={{ ...s.td, ...s.mono, textAlign: 'center', color: diffColor, fontWeight: 600 }}>
                        {diff === null ? '—' : `${diff > 0 ? '+' : ''}${diff}pp`}
                      </td>
                    </tr>
                  );
                })}
                {/* Grand total row */}
                <tr style={{ background: '#f0f4ff', fontWeight: 700 }}>
                  <td style={{ ...s.td, fontWeight: 700 }}>TOTAL</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(grandTotals.total)}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(monthlyData.reduce((s, d) => s + d.ios, 0))}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(monthlyData.reduce((s, d) => s + d.android, 0))}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(monthlyData.reduce((s, d) => s + d.qrScan, 0))}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right', borderLeft: '2px solid #f3f4f6' }}>{fmt(grandTotals.organicTotal)}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(monthlyData.reduce((s, d) => s + d.referral, 0))}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(monthlyData.reduce((s, d) => s + d.googleMaps, 0))}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right' }}>{fmt(monthlyData.reduce((s, d) => s + d.socialOther, 0))}</td>
                  <td style={{ ...s.td, ...s.mono, textAlign: 'right', borderLeft: '2px solid #f3f4f6' }}>{fmt(grandTotals.marketingTotal)}</td>
                  <td style={{ ...s.td, textAlign: 'center' }}>
                    <span style={s.badge(COLORS.primary)}>{pct(grandTotals.marketingPct)}</span>
                  </td>
                  <td style={{ ...s.td, textAlign: 'center' }}>—</td>
                </tr>
              </tbody>
            </table>
            <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>
              * QR Scan estimated via timing proxy model (Model B, conservative). Google Maps estimated at 5.3% of H5 total per CDP sample.
            </div>
          </div>
        </div>

        {/* ── Section 4: Stacked Channel Composition ── */}
        <div style={s.section}>
          <h2 style={s.sectionTitle}>渠道构成趋势 Channel Composition Over Time</h2>
          <div style={s.card}>
            <ResponsiveContainer width="100%" height={420}>
              <BarChart data={stackedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip content={<StackedTooltip />} />
                <Legend wrapperStyle={{ fontSize: 13 }} />
                {/* Organic (cool) */}
                <Bar dataKey="iOS Organic" stackId="a" fill={COLORS.iosOrganic} />
                <Bar dataKey="Android Organic" stackId="a" fill={COLORS.androidOrganic} />
                <Bar dataKey="QR Scan (est.)" stackId="a" fill={COLORS.qrScan} />
                {/* Marketing (warm) */}
                <Bar dataKey="Referral" stackId="a" fill={COLORS.referral} />
                <Bar dataKey="Google Maps (est.)" stackId="a" fill={COLORS.googleMaps} />
                <Bar dataKey="Social/Other" stackId="a" fill={COLORS.socialOther} />
              </BarChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 32, marginTop: 8, fontSize: 12, color: '#6b7280' }}>
              <span><span style={{ display: 'inline-block', width: 40, height: 4, background: 'linear-gradient(90deg, #93C5FD, #6EE7B7, #A5B4FC)', borderRadius: 2, verticalAlign: 'middle', marginRight: 6 }} />Organic / Store-Driven (cool)</span>
              <span><span style={{ display: 'inline-block', width: 40, height: 4, background: 'linear-gradient(90deg, #FCA5A5, #FDBA74, #FDE68A)', borderRadius: 2, verticalAlign: 'middle', marginRight: 6 }} />Marketing-Attributable (warm)</span>
            </div>
          </div>
        </div>

        {/* ── Section 5: Methodology & Limitations ── */}
        <div style={s.section}>
          <div
            style={{ ...s.sectionTitle, ...s.collapsible }}
            onClick={() => setMethodOpen(!methodOpen)}
          >
            <span style={{ transform: methodOpen ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s', display: 'inline-block' }}>&#9654;</span>
            数据说明与已知局限 Methodology &amp; Limitations
          </div>
          {methodOpen && (
            <div style={s.card}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                <div>
                  <h4 style={{ fontSize: 14, color: '#1A365D', marginBottom: 8 }}>排除法 Exclusion Method</h4>
                  <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.7, margin: 0 }}>{methodology.exclusionMethod}</p>
                </div>
                <div>
                  <h4 style={{ fontSize: 14, color: '#1A365D', marginBottom: 8 }}>时间代理模型 Timing Proxy</h4>
                  <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.7, margin: 0 }}>{methodology.timingProxy}</p>
                </div>
              </div>
              <div style={{ marginTop: 16 }}>
                <h4 style={{ fontSize: 14, color: '#1A365D', marginBottom: 8 }}>下限估算说明</h4>
                <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.7, margin: 0, background: '#FEF3C7', padding: '10px 14px', borderRadius: 8, borderLeft: '3px solid #DCBD23' }}>
                  {methodology.floorEstimate}
                </p>
              </div>
              <div style={{ marginTop: 16 }}>
                <h4 style={{ fontSize: 14, color: '#1A365D', marginBottom: 8 }}>已知局限 Known Limitations</h4>
                <ul style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.8, margin: 0, paddingLeft: 20 }}>
                  {methodology.limitations.map((l, i) => <li key={i}>{l}</li>)}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* ── Section 6: Recommendations ── */}
        <div style={s.section}>
          <h2 style={s.sectionTitle}>行动建议 Next Steps</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {methodology.recommendations.map((r, i) => (
              <div key={i} style={s.recCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#1A365D' }}>{r.title}</span>
                  <span style={s.badge(r.priority === '高' ? '#EF4444' : '#F59E0B')}>{r.priority}</span>
                </div>
                <p style={{ fontSize: 12, color: '#6b7280', margin: 0, lineHeight: 1.6 }}>{r.desc}</p>
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>Timeline: {r.timeline}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Footer ── */}
        <div style={{ textAlign: 'center', fontSize: 12, color: '#9ca3af', paddingTop: 16, borderTop: '1px solid #e5e7eb' }}>
          曾翔宇 &middot; DBA Team &middot; 瑞幸咖啡北美 &middot; 2026-03-26 &nbsp;|&nbsp; LCNA-MKT-2026-004 &nbsp;|&nbsp; Data source: salescrm (aws-luckyus-salescrm-rw)
        </div>
      </div>
    </div>
  );
}
