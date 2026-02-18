/**
 * UC-SC-02: Waste Command Center — React/Recharts Dashboard
 *
 * Standalone visualization component for waste prediction & reduction metrics.
 * Data source: MySQL test schema on aws-luckyus-dbatest-rw
 *
 * Usage:
 *   import WasteCommandCenter from './WasteCommandCenter';
 *   <WasteCommandCenter data={apiData} />
 *
 * Expected `data` prop shape — see PropTypes at bottom of file.
 */

import React, { useState, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Area, AreaChart, ReferenceLine
} from 'recharts';

// ─── Constants ──────────────────────────────────────────────────────────────

const COLORS = {
  CRITICAL: '#ef4444',
  HIGH:     '#f97316',
  MEDIUM:   '#eab308',
  LOW:      '#22c55e',
  ULTRA_SHORT: '#ef4444',
  SHORT:       '#f97316',
  MEDIUM_TIER: '#eab308',
  LONG:        '#22c55e',
  v1Model:     '#22c55e',
  baseline:    '#ef4444',
  target:      '#3b82f6',
  primary:     '#6366f1',
  secondary:   '#8b5cf6',
  muted:       '#64748b',
};

const RISK_TIERS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
const SHELF_TIERS = ['ULTRA_SHORT', 'SHORT', 'MEDIUM', 'LONG'];

const STORE_NAMES = {
  1127:  '8th Ave & Broadway',
  1128:  '28th St & 6th Ave',
  1140:  '100 Maiden Lane',
  1141:  '54th St & 8th Ave',
  20008: 'JFK Terminal 1',
  20010: 'Midtown East',
  20011: 'Financial District',
  20027: 'Union Square',
  20031: 'Herald Square',
  20032: 'Columbus Circle',
};

const STORE_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316',
  '#eab308', '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6',
];

const formatCurrency = (val) => `$${Number(val || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
const formatPct = (val) => `${(Number(val || 0) * 100).toFixed(1)}%`;
const formatNum = (val) => Number(val || 0).toLocaleString('en-US');

// ─── Sub-components ─────────────────────────────────────────────────────────

function StatCard({ title, value, format, thresholds, icon }) {
  const numVal = Number(value || 0);
  let color = '#22c55e';
  if (thresholds) {
    for (const t of thresholds) {
      if (numVal >= t.value) color = t.color;
    }
  }

  const displayValue = format === 'currency' ? formatCurrency(numVal)
    : format === 'percent' ? formatPct(numVal)
    : formatNum(numVal);

  return (
    <div style={{
      background: '#1e293b', borderRadius: 8, padding: '16px 20px',
      border: `2px solid ${color}33`, minWidth: 150, flex: 1,
    }}>
      <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {icon && <span style={{ marginRight: 6 }}>{icon}</span>}
        {title}
      </div>
      <div style={{ color, fontSize: 28, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
        {displayValue}
      </div>
    </div>
  );
}

function SectionHeader({ children }) {
  return (
    <h3 style={{
      color: '#e2e8f0', fontSize: 16, fontWeight: 600, margin: '24px 0 12px',
      paddingBottom: 8, borderBottom: '1px solid #334155',
    }}>
      {children}
    </h3>
  );
}

function ChartCard({ title, description, children, style }) {
  return (
    <div style={{
      background: '#1e293b', borderRadius: 8, padding: 16,
      border: '1px solid #334155', ...style,
    }}>
      <div style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{title}</div>
      {description && <div style={{ color: '#64748b', fontSize: 11, marginBottom: 12 }}>{description}</div>}
      {children}
    </div>
  );
}

function AlertBadge({ type }) {
  const colors = {
    CRITICAL: '#ef4444', WARNING: '#f97316', BIAS: '#eab308',
    TREND: '#3b82f6', EXPIRY_SURGE: '#a855f7', COVERAGE: '#64748b',
  };
  return (
    <span style={{
      background: `${colors[type] || '#64748b'}22`,
      color: colors[type] || '#64748b',
      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
    }}>
      {type}
    </span>
  );
}

function StatusBadge({ status }) {
  const colors = {
    SUCCESS: '#22c55e', PARTIAL: '#f97316', FAILED: '#ef4444',
    RUNNING: '#3b82f6', PENDING: '#eab308',
  };
  return (
    <span style={{
      background: `${colors[status] || '#64748b'}22`,
      color: colors[status] || '#64748b',
      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
    }}>
      {status}
    </span>
  );
}

// ─── Tooltip Formatters ─────────────────────────────────────────────────────

function CurrencyTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 6, padding: 10, fontSize: 12 }}>
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: {formatCurrency(p.value)}
        </div>
      ))}
    </div>
  );
}

function PctTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 6, padding: 10, fontSize: 12 }}>
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginBottom: 2 }}>
          {p.name}: {formatPct(p.value)}
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function WasteCommandCenter({ data = {} }) {
  const [selectedStore, setSelectedStore] = useState('ALL');

  const {
    summary = {},
    wasteRateTrend = [],
    riskDistribution = [],
    wasteByCost = [],
    forecastAccuracy = [],
    wasteByTier = [],
    alerts = [],
    transfers = [],
    pipelineRuns = [],
  } = data;

  // Filter data by selected store
  const filteredTrend = useMemo(() => {
    if (selectedStore === 'ALL') return wasteRateTrend;
    return wasteRateTrend.filter(r => String(r.store_id) === selectedStore);
  }, [wasteRateTrend, selectedStore]);

  const storeOptions = useMemo(() => {
    const ids = [...new Set(wasteRateTrend.map(r => r.store_id))].sort();
    return ids.map(id => ({ id, name: STORE_NAMES[id] || `Store ${id}` }));
  }, [wasteRateTrend]);

  // Pivot waste trend for multi-line chart: [{date, store1: rate, store2: rate, ...}]
  const pivotedTrend = useMemo(() => {
    const byDate = {};
    const source = selectedStore === 'ALL' ? wasteRateTrend : filteredTrend;
    source.forEach(r => {
      const key = r.date;
      if (!byDate[key]) byDate[key] = { date: key };
      const storeName = STORE_NAMES[r.store_id] || `Store ${r.store_id}`;
      byDate[key][storeName] = r.waste_rate;
    });
    return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));
  }, [wasteRateTrend, filteredTrend, selectedStore]);

  const trendStoreNames = useMemo(() => {
    if (selectedStore !== 'ALL') {
      return [STORE_NAMES[Number(selectedStore)] || `Store ${selectedStore}`];
    }
    return [...new Set(wasteRateTrend.map(r => STORE_NAMES[r.store_id] || `Store ${r.store_id}`))];
  }, [wasteRateTrend, selectedStore]);

  return (
    <div style={{ background: '#0f172a', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif', padding: 24, minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: '#f1f5f9' }}>
            Waste Command Center
          </h1>
          <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>
            UC-SC-02 | 10 Manhattan Stores | Auto-refresh 5m
          </div>
        </div>
        <div>
          <select
            value={selectedStore}
            onChange={(e) => setSelectedStore(e.target.value)}
            style={{
              background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155',
              borderRadius: 6, padding: '8px 12px', fontSize: 13,
            }}
          >
            <option value="ALL">All Stores</option>
            {storeOptions.map(s => (
              <option key={s.id} value={String(s.id)}>{s.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <StatCard
          title="Waste Rate (7d)"
          value={summary.waste_rate_7d}
          format="percent"
          thresholds={[
            { value: 0, color: '#22c55e' },
            { value: 0.04, color: '#eab308' },
            { value: 0.05, color: '#f97316' },
            { value: 0.08, color: '#ef4444' },
          ]}
        />
        <StatCard
          title="Waste Cost (7d)"
          value={summary.waste_cost_7d}
          format="currency"
          thresholds={[
            { value: 0, color: '#22c55e' },
            { value: 500, color: '#eab308' },
            { value: 1000, color: '#ef4444' },
          ]}
        />
        <StatCard
          title="v1 MAPE"
          value={summary.v1_mape}
          format="percent"
          thresholds={[
            { value: 0, color: '#22c55e' },
            { value: 0.20, color: '#eab308' },
            { value: 0.25, color: '#f97316' },
            { value: 0.35, color: '#ef4444' },
          ]}
        />
        <StatCard
          title="CRITICAL Batches"
          value={summary.critical_batches}
          format="number"
          thresholds={[
            { value: 0, color: '#22c55e' },
            { value: 5, color: '#eab308' },
            { value: 10, color: '#f97316' },
            { value: 20, color: '#ef4444' },
          ]}
        />
        <StatCard
          title="Active Alerts"
          value={summary.active_alerts}
          format="number"
          thresholds={[
            { value: 0, color: '#22c55e' },
            { value: 1, color: '#eab308' },
            { value: 3, color: '#f97316' },
            { value: 5, color: '#ef4444' },
          ]}
        />
        <StatCard
          title="Pending Transfers"
          value={summary.pending_transfers}
          format="number"
          thresholds={[
            { value: 0, color: '#3b82f6' },
            { value: 1, color: '#22c55e' },
          ]}
        />
      </div>

      {/* Row 2: Waste Rate Trend + Risk Distribution */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 16 }}>
        <ChartCard title="Waste Rate Trend by Store" description="Daily waste rate per store">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={pivotedTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tickFormatter={formatPct} tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip content={<PctTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine y={0.05} stroke={COLORS.target} strokeDasharray="6 6" label={{ value: '5% Warning', fill: COLORS.target, fontSize: 10 }} />
              <ReferenceLine y={0.08} stroke={COLORS.CRITICAL} strokeDasharray="6 6" label={{ value: '8% Critical', fill: COLORS.CRITICAL, fontSize: 10 }} />
              {trendStoreNames.map((name, i) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={STORE_COLORS[i % STORE_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Risk Distribution" description="Batch risk tier breakdown">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={riskDistribution}
                dataKey="count"
                nameKey="tier"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={90}
                paddingAngle={2}
                label={({ tier, count }) => `${tier}: ${count}`}
                labelLine={{ stroke: '#64748b' }}
              >
                {riskDistribution.map((entry) => (
                  <Cell key={entry.tier} fill={COLORS[entry.tier] || COLORS.muted} />
                ))}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Row 3: Forecast Accuracy + Waste by Tier */}
      <SectionHeader>Forecast Performance & Waste Breakdown</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <ChartCard title="Forecast Accuracy: v1 vs Baseline" description="Daily MAPE — v1 model (green) vs iReplenishment (red)">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={forecastAccuracy}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tickFormatter={formatPct} tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 'auto']} />
              <Tooltip content={<PctTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine y={0.25} stroke={COLORS.target} strokeDasharray="6 6" label={{ value: 'Target 25%', fill: COLORS.target, fontSize: 10 }} />
              <Area type="monotone" dataKey="v1_mape" name="v1 Model" stroke={COLORS.v1Model} fill={`${COLORS.v1Model}22`} strokeWidth={2} />
              <Area type="monotone" dataKey="baseline_mape" name="iReplenishment" stroke={COLORS.baseline} fill={`${COLORS.baseline}11`} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Daily Waste Cost by Shelf-Life Tier" description="Stacked daily waste cost breakdown">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={wasteByTier}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tickFormatter={formatCurrency} tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip content={<CurrencyTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="ULTRA_SHORT" stackId="a" fill={COLORS.ULTRA_SHORT} />
              <Bar dataKey="SHORT" stackId="a" fill={COLORS.SHORT} />
              <Bar dataKey="MEDIUM" stackId="a" fill={COLORS.MEDIUM_TIER} />
              <Bar dataKey="LONG" stackId="a" fill={COLORS.LONG} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Row 4: Waste Cost by Store */}
      <ChartCard
        title="Waste Cost by Store"
        description="Total waste cost per store in the selected period"
        style={{ marginBottom: 16 }}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={wasteByCost} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis type="number" tickFormatter={formatCurrency} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis dataKey="store_name" type="category" width={150} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip content={<CurrencyTooltip />} />
            <Bar dataKey="waste_cost" name="Waste Cost" radius={[0, 4, 4, 0]}>
              {wasteByCost.map((entry, i) => {
                const rate = entry.waste_rate || 0;
                const color = rate >= 0.08 ? COLORS.CRITICAL
                  : rate >= 0.05 ? COLORS.HIGH
                  : rate >= 0.03 ? COLORS.MEDIUM
                  : COLORS.LOW;
                return <Cell key={i} fill={color} />;
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Row 5: Alerts + Transfers Tables */}
      <SectionHeader>Alerts & Transfer Recommendations</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Alerts Table */}
        <ChartCard title="Active Alerts" description="Unacknowledged waste alerts (last 7d)">
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <th style={thStyle}>Date</th>
                  <th style={thStyle}>Type</th>
                  <th style={thStyle}>Entity</th>
                  <th style={thStyle}>Value</th>
                  <th style={thStyle}>Action</th>
                </tr>
              </thead>
              <tbody>
                {alerts.length === 0 && (
                  <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: '#64748b' }}>No active alerts</td></tr>
                )}
                {alerts.map((a, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #1e293b' }}>
                    <td style={tdStyle}>{a.alert_date}</td>
                    <td style={tdStyle}><AlertBadge type={a.alert_type} /></td>
                    <td style={tdStyle}>{a.entity_name}</td>
                    <td style={{ ...tdStyle, fontVariantNumeric: 'tabular-nums' }}>{formatPct(a.metric_value)}</td>
                    <td style={{ ...tdStyle, color: '#94a3b8', fontSize: 11 }}>{a.recommended_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>

        {/* Transfers Table */}
        <ChartCard title="Pending Transfers" description="Transfer recommendations with net benefit">
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <th style={thStyle}>From</th>
                  <th style={thStyle}>To</th>
                  <th style={thStyle}>Item</th>
                  <th style={thStyle}>Qty</th>
                  <th style={thStyle}>Net $</th>
                  <th style={thStyle}>Hrs Left</th>
                </tr>
              </thead>
              <tbody>
                {transfers.length === 0 && (
                  <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: '#64748b' }}>No pending transfers</td></tr>
                )}
                {transfers.map((t, i) => {
                  const hrsColor = t.hours_left < 12 ? COLORS.CRITICAL
                    : t.hours_left < 24 ? COLORS.HIGH
                    : t.hours_left < 48 ? COLORS.MEDIUM
                    : COLORS.LOW;
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={tdStyle}>{t.source_store_name}</td>
                      <td style={tdStyle}>{t.dest_store_name}</td>
                      <td style={{ ...tdStyle, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.goods_name}</td>
                      <td style={{ ...tdStyle, fontVariantNumeric: 'tabular-nums' }}>{t.transfer_qty}</td>
                      <td style={{ ...tdStyle, color: '#22c55e', fontVariantNumeric: 'tabular-nums' }}>{formatCurrency(t.net_benefit)}</td>
                      <td style={{ ...tdStyle, color: hrsColor, fontVariantNumeric: 'tabular-nums' }}>{Number(t.hours_left).toFixed(1)}h</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </ChartCard>
      </div>

      {/* Row 6: Pipeline Health */}
      <SectionHeader>Pipeline Health</SectionHeader>
      <ChartCard title="Recent Pipeline Runs" description="sp_waste_daily_refresh execution history">
        <div style={{ maxHeight: 280, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155' }}>
                <th style={thStyle}>Run ID</th>
                <th style={thStyle}>Date</th>
                <th style={thStyle}>Start</th>
                <th style={thStyle}>Duration</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Error</th>
              </tr>
            </thead>
            <tbody>
              {pipelineRuns.length === 0 && (
                <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: '#64748b' }}>No pipeline runs</td></tr>
              )}
              {pipelineRuns.map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 11 }}>{r.run_id}</td>
                  <td style={tdStyle}>{r.data_date}</td>
                  <td style={tdStyle}>{r.run_start}</td>
                  <td style={{ ...tdStyle, fontVariantNumeric: 'tabular-nums' }}>{r.duration_seconds != null ? `${r.duration_seconds}s` : '-'}</td>
                  <td style={tdStyle}><StatusBadge status={r.status} /></td>
                  <td style={{ ...tdStyle, color: '#ef4444', fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.error_message || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>

      {/* Footer */}
      <div style={{ marginTop: 24, color: '#475569', fontSize: 11, textAlign: 'center' }}>
        UC-SC-02 Waste Prediction & Reduction | Data source: test schema @ aws-luckyus-dbatest-rw | Target: 2-4% waste rate, &lt;25% MAPE
      </div>
    </div>
  );
}

// ─── Table Styles ───────────────────────────────────────────────────────────

const thStyle = {
  textAlign: 'left',
  padding: '6px 8px',
  color: '#94a3b8',
  fontWeight: 600,
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: 0.3,
  position: 'sticky',
  top: 0,
  background: '#1e293b',
};

const tdStyle = {
  padding: '6px 8px',
  color: '#cbd5e1',
};

// ─── Data Loading Helper ────────────────────────────────────────────────────

/**
 * SQL queries to populate the data prop.
 * Execute these against aws-luckyus-dbatest-rw (schema: test).
 */
export const DATA_QUERIES = {
  summary: `
    SELECT
      (SELECT waste_rate FROM test.waste_summary WHERE period_type='ROLLING_7D' AND dimension_type='OVERALL' ORDER BY period_end DESC LIMIT 1) AS waste_rate_7d,
      (SELECT total_waste_cost FROM test.waste_summary WHERE period_type='ROLLING_7D' AND dimension_type='OVERALL' ORDER BY period_end DESC LIMIT 1) AS waste_cost_7d,
      (SELECT waste_mape FROM test.waste_summary WHERE period_type='ROLLING_7D' AND dimension_type='OVERALL' ORDER BY period_end DESC LIMIT 1) AS v1_mape,
      (SELECT COUNT(*) FROM test.waste_batch_risk_score WHERE score_date = CURDATE() AND risk_tier='CRITICAL') AS critical_batches,
      (SELECT COUNT(*) FROM test.waste_alerts WHERE is_acknowledged=FALSE AND alert_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)) AS active_alerts,
      (SELECT COUNT(*) FROM test.waste_transfer_recommendations WHERE status='PENDING' AND recommendation_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)) AS pending_transfers
  `,

  wasteRateTrend: `
    SELECT
      waste_date AS date,
      shop_dept_id AS store_id,
      shop_name AS store_name,
      SUM(waste_qty_total) / NULLIF(SUM(waste_qty_total) + SUM(consumption_qty), 0) AS waste_rate
    FROM test.waste_daily_detail
    WHERE waste_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
    GROUP BY waste_date, shop_dept_id, shop_name
    ORDER BY waste_date, shop_dept_id
  `,

  riskDistribution: `
    SELECT risk_tier AS tier, COUNT(*) AS count
    FROM test.waste_batch_risk_score
    WHERE score_date = (SELECT MAX(score_date) FROM test.waste_batch_risk_score WHERE score_date <= CURDATE())
    GROUP BY risk_tier
    ORDER BY FIELD(risk_tier, 'CRITICAL','HIGH','MEDIUM','LOW')
  `,

  wasteByCost: `
    SELECT
      CONCAT(shop_dept_id, ' - ', shop_name) AS store_name,
      SUM(waste_cost) AS waste_cost,
      SUM(waste_qty_total) / NULLIF(SUM(waste_qty_total) + SUM(consumption_qty), 0) AS waste_rate
    FROM test.waste_daily_detail
    WHERE waste_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    GROUP BY shop_dept_id, shop_name
    ORDER BY waste_cost DESC
  `,

  forecastAccuracy: `
    SELECT
      consumption_date AS date,
      AVG(v1_abs_pct_error) AS v1_mape,
      AVG(abs_pct_error) AS baseline_mape
    FROM test.waste_consumption_daily
    WHERE consumption_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
      AND actual_consumption > 0
    GROUP BY consumption_date
    ORDER BY consumption_date
  `,

  wasteByTier: `
    SELECT
      waste_date AS date,
      SUM(CASE WHEN shelf_life_tier='ULTRA_SHORT' THEN waste_cost ELSE 0 END) AS ULTRA_SHORT,
      SUM(CASE WHEN shelf_life_tier='SHORT' THEN waste_cost ELSE 0 END) AS SHORT,
      SUM(CASE WHEN shelf_life_tier='MEDIUM' THEN waste_cost ELSE 0 END) AS MEDIUM,
      SUM(CASE WHEN shelf_life_tier='LONG' THEN waste_cost ELSE 0 END) AS LONG
    FROM test.waste_daily_detail
    WHERE waste_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
    GROUP BY waste_date
    ORDER BY waste_date
  `,

  alerts: `
    SELECT alert_date, alert_type, entity_name, metric_value, recommended_action
    FROM test.waste_alerts
    WHERE is_acknowledged = FALSE AND alert_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    ORDER BY alert_date DESC, FIELD(alert_type,'CRITICAL','WARNING','BIAS','TREND','EXPIRY_SURGE')
    LIMIT 30
  `,

  transfers: `
    SELECT source_store_name, dest_store_name, goods_name, transfer_qty,
           net_benefit, source_hours_to_expiry AS hours_left
    FROM test.waste_transfer_recommendations
    WHERE status='PENDING' AND recommendation_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    ORDER BY net_benefit DESC
    LIMIT 30
  `,

  pipelineRuns: `
    SELECT run_id, data_date_start AS data_date, run_start, duration_seconds,
           status, COALESCE(error_message,'') AS error_message
    FROM test.waste_pipeline_run_log
    WHERE step_name = 'sp_waste_daily_refresh'
    ORDER BY run_start DESC
    LIMIT 14
  `,
};
