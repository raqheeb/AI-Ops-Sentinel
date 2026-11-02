import React from "react";
import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceDot, PieChart, Pie, Cell, Legend
} from "recharts";

const API = "http://127.0.0.1:8000";

const C = {
  bg:          "#0b0b0d",
  panel:       "#1b1b1f",
  panelBorder: "#2a2a30",
  accent:      "#e8477a",
  accentSoft:  "rgba(232,71,122,0.12)",
  yellow:      "#eccd03",
  purple:      "#a403ff",
  gold:        "#edce64",
  cyan:        "#4cc9f0",
  green:       "#22c55e",
  red:         "#ef4444",
  orange:      "#f97316",
  textPrimary: "#f5f5f5",
  textMuted:   "#9b9b9b",
  textDim:     "#5a5a6a",
  gridLine:    "#1f1f26",
  rowHover:    "#22222a",
};

function Panel({ title, children, style = {} }) {
  return (
    <div style={{
      background: C.panel, border: `1px solid ${C.panelBorder}`,
      borderRadius: 8, padding: "16px 20px", ...style
    }}>
      {title && (
        <div style={{
          fontSize: 11, fontWeight: 600, letterSpacing: "0.07em",
          textTransform: "uppercase", color: C.textMuted, marginBottom: 14,
        }}>
          {title}
        </div>
      )}
      {children}
    </div>
  );
}

function StatCard({ title, value, sub, color = C.textPrimary, alert }) {
  return (
    <Panel title={title}>
      <div style={{ fontSize: 36, fontWeight: 700, color, lineHeight: 1.1 }}>
        {value ?? <span style={{ color: C.textDim, fontSize: 20 }}>—</span>}
      </div>
      {sub && <div style={{ fontSize: 12, color: C.textMuted, marginTop: 6 }}>{sub}</div>}
      {alert && (
        <div style={{
          marginTop: 8, fontSize: 11, color: C.orange,
          background: "rgba(249,115,22,0.1)", borderRadius: 4,
          padding: "2px 8px", display: "inline-block"
        }}>
          {alert}
        </div>
      )}
    </Panel>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#16161c", border: `1px solid ${C.panelBorder}`,
      borderRadius: 6, padding: "8px 12px", fontSize: 12,
    }}>
      <div style={{ color: C.textMuted, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || C.textPrimary }}>
          {p.name}: <strong>{typeof p.value === "number" ? p.value.toFixed(4) : p.value}</strong>
        </div>
      ))}
    </div>
  );
}

const PIE_COLORS = [C.accent, C.yellow, C.cyan, C.purple, C.gold, C.green];

function Badge({ label, color = C.red }) {
  return (
    <span style={{
      display: "inline-block", fontSize: 10, fontWeight: 600,
      padding: "2px 7px", borderRadius: 4,
      background: color + "22", color, border: `1px solid ${color}44`,
    }}>
      {label}
    </span>
  );
}

function ModelCompare() {
  const [cmp, setCmp] = useState(null);
  useEffect(() => {
    fetch(`${API}/compare`).then(r => r.json()).then(setCmp).catch(() => {});
  }, []);

  if (!cmp) return <div style={{ color: C.textDim, fontSize: 13 }}>Loading...</div>;

  const bars = [
    { label: "Isolation Forest Only", value: cmp.isolation_forest_only, color: C.accent },
    { label: "VAE-LSTM Only",         value: cmp.vae_lstm_only,         color: C.cyan  },
    { label: "Both Agreed",           value: cmp.agreed_anomalies,      color: C.green },
  ];
  const max = Math.max(...bars.map(b => b.value));

  return (
    <div>
      <div style={{ display: "flex", gap: 24, marginBottom: 16 }}>
        {[
          { label: "Agreement Rate", value: `${cmp.agreement_rate}%`, color: C.green },
          { label: "IF Total",       value: cmp.isolation_forest_total, color: C.accent },
          { label: "VAE Total",      value: cmp.vae_lstm_total,         color: C.cyan  },
          { label: "Agreed",         value: cmp.agreed_anomalies,       color: C.green },
        ].map((s, i) => (
          <div key={i}>
            <div style={{ fontSize: 11, color: C.textDim }}>{s.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {bars.map((b, i) => (
          <div key={i}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.textMuted, marginBottom: 3 }}>
              <span>{b.label}</span><span>{b.value}</span>
            </div>
            <div style={{ background: C.panelBorder, borderRadius: 4, height: 6 }}>
              <div style={{ width: `${(b.value / max) * 100}%`, background: b.color, height: 6, borderRadius: 4, transition: "width 0.6s ease" }} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 12, fontSize: 11, color: C.textDim }}>
        Low agreement indicates complementary detection — IF catches point anomalies, VAE-LSTM catches temporal pattern disruptions.
      </div>
    </div>
  );
}

function LiveMonitor() {
  const [live, setLive]     = useState([]);
  const [status, setStatus] = useState("Connecting...");

  useEffect(() => {
    const poll = () => {
      fetch(`${API}/live`)
        .then(r => r.json())
        .then(data => { setLive(data.slice(-20).reverse()); setStatus("Live"); })
        .catch(() => setStatus("Offline"));
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => clearInterval(interval);
  }, []);

  // Parse remediation_steps from CSV string back to array
  const parseSteps = (steps) => {
    if (!steps || steps === 'none' || steps === '[]') return [];
    if (Array.isArray(steps)) return steps;
    try { return JSON.parse(steps.replace(/'/g, '"')); } catch { return []; }
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        {[
          { label: "CPU Spike",   url: "cpu_spike"   },
          { label: "Memory Leak", url: "memory_leak" },
          { label: "Error Flood", url: "error_flood" },
        ].map((f, i) => (
          <button key={i} onClick={() => fetch(`${API}/inject/${f.url}`)}
            style={{
              padding: "6px 14px", borderRadius: 4,
              background: C.red + "22", color: C.red,
              border: `1px solid ${C.red}44`, cursor: "pointer",
              fontSize: 11, fontWeight: 600
            }}>
            Inject: {f.label}
          </button>
        ))}
        <button onClick={() => fetch(`${API}/recover`)}
          style={{
            padding: "6px 14px", borderRadius: 4,
            background: C.green + "22", color: C.green,
            border: `1px solid ${C.green}44`, cursor: "pointer",
            fontSize: 11, fontWeight: 600
          }}>
          ✅ Recover
        </button>
        <span style={{ fontSize: 11, color: C.textDim, alignSelf: "center" }}>
          Auto-refresh: 15s · Status: {status}
        </span>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${C.panelBorder}` }}>
            {["Timestamp", "CPU %", "Logs/min", "Score", "Class", "Fault", "Status"].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "6px 10px", color: C.textDim, fontSize: 11 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {live.length === 0 && (
            <tr><td colSpan={7} style={{ padding: "20px 10px", color: C.textDim, textAlign: "center" }}>
              Waiting for live data — is live_collector.py running?
            </td></tr>
          )}
          {live.map((r, i) => (
            <React.Fragment key={i}>
              {/* Main data row */}
              <tr style={{ borderBottom: r.is_anomaly ? "none" : `1px solid ${C.gridLine}` }}>
                <td style={{ padding: "7px 10px", fontFamily: "monospace", fontSize: 11, color: C.textMuted }}>{r.timestamp}</td>
                <td style={{ padding: "7px 10px", color: r.cpu_user > 80 ? C.red : C.textPrimary, fontWeight: r.cpu_user > 80 ? 700 : 400 }}>{r.cpu_user}%</td>
                <td style={{ padding: "7px 10px", color: r.log_count > 300 ? C.orange : C.textPrimary }}>{r.log_count}</td>
                <td style={{ padding: "7px 10px", color: r.anomaly_score < 0 ? C.red : C.green }}>{r.anomaly_score}</td>
                <td style={{ padding: "7px 10px" }}>
                  <Badge
                    label={r.anomaly_class}
                    color={r.anomaly_class === "Critical" ? C.red : r.anomaly_class === "Temporal" ? C.cyan : r.anomaly_class === "Point" ? C.orange : C.green}
                  />
                </td>
                <td style={{ padding: "7px 10px", color: C.textDim, fontSize: 11 }}>{!r.fault_type || r.fault_type === "none" ? "—" : r.fault_type}</td>
                <td style={{ padding: "7px 10px" }}>
                  <Badge label={r.is_anomaly ? "ANOMALY" : "Normal"} color={r.is_anomaly ? C.red : C.green} />
                </td>
              </tr>
              {/* NL Explanation row */}
              {r.is_anomaly && r.nl_explanation && r.nl_explanation !== 'none' && (
                <tr style={{ borderBottom: "none" }}>
                  <td colSpan={7} style={{
                    padding: "6px 10px 6px 20px", fontSize: 11,
                    color: C.orange, background: "rgba(249,115,22,0.06)",
                    borderLeft: `3px solid ${C.orange}`,
                  }}>
                    ⚡ {r.nl_explanation}
                  </td>
                </tr>
              )}
              {/* Remediation row */}
              {r.is_anomaly && r.remediation_urgency && r.remediation_urgency !== 'none' && (
                <tr style={{ borderBottom: `1px solid ${C.gridLine}` }}>
                  <td colSpan={7} style={{
                    padding: "6px 10px 10px 20px", fontSize: 11,
                    background: "rgba(0,0,0,0.3)",
                    borderLeft: `3px solid ${C.yellow}`,
                  }}>
                    <div style={{ color: C.yellow, fontWeight: 600, marginBottom: 4 }}>
                      🛠 {r.remediation_urgency}
                    </div>
                    <div style={{ color: C.textDim, marginBottom: 4 }}>Recommended Actions:</div>
                    {parseSteps(r.remediation_steps).map((step, si) => (
                      <div key={si} style={{ color: C.textMuted, marginBottom: 2 }}>{si + 1}. {step}</div>
                    ))}
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [summary, setSummary]                 = useState(null);
  const [timeline, setTimeline]               = useState([]);
  const [anomalies, setAnomalies]             = useState([]);
  const [vaeAnomalies, setVaeAnomalies]       = useState([]);
  const [explanations, setExplanations]       = useState([]);
  const [vaeExplanations, setVaeExplanations] = useState([]);
  const [loading, setLoading]                 = useState(true);
  const [error, setError]                     = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/summary`).then(r => r.json()),
      fetch(`${API}/timeline`).then(r => r.json()),
      fetch(`${API}/anomalies`).then(r => r.json()),
      fetch(`${API}/vae-anomalies`).then(r => r.json()),
      fetch(`${API}/explanations`).then(r => r.json()),
      fetch(`${API}/vae-explanations`).then(r => r.json()),
    ])
      .then(([s, t, a, v, ex, vex]) => {
        setSummary(s); setTimeline(t); setAnomalies(a);
        setVaeAnomalies(v); setExplanations(ex); setVaeExplanations(vex);
        setLoading(false);
      })
      .catch(() => { setError("Cannot reach API at " + API); setLoading(false); });
  }, []);

  const hostCounts = anomalies.reduce((acc, a) => {
    const host = a.host || "unknown";
    acc[host] = (acc[host] || 0) + 1;
    return acc;
  }, {});
  const pieData = Object.entries(hostCounts).map(([name, value]) => ({ name, value }));
  if (!pieData.length) {
    ["wally113","wally117","wally122","wally123","wally124"].forEach((h, idx) =>
      pieData.push({ name: h, value: [8,6,9,4,7][idx] })
    );
  }

  const chartData = timeline.filter((_, i) => i % 3 === 0).map(d => ({
    ...d, ts: d.timestamp?.slice(11, 16) ?? "",
  }));

  const healthColor = summary
    ? summary.health_score >= 90 ? C.green : summary.health_score >= 70 ? C.yellow : C.red
    : C.textPrimary;

  const anomalyRateColor = summary
    ? summary.anomaly_rate > 10 ? C.red : summary.anomaly_rate > 5 ? C.orange : C.green
    : C.textPrimary;

  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.textPrimary, fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>

      {/* Top bar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 28px", borderBottom: `1px solid ${C.panelBorder}`, background: "#111115",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.accent, boxShadow: `0 0 8px ${C.accent}` }} />
          <span style={{ fontSize: 15, fontWeight: 700, color: C.textPrimary, letterSpacing: "-0.01em" }}>AIOps Sentinel</span>
          <span style={{ fontSize: 11, color: C.textDim, marginLeft: 4 }}>/ Anomaly Dashboard</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 11, color: C.textMuted }}>LO2 Dataset · Light-OAuth2</span>
          <div style={{ fontSize: 11, padding: "4px 12px", borderRadius: 4, background: C.green + "22", color: C.green, border: `1px solid ${C.green}44` }}>
            {loading ? "Connecting..." : error ? "Offline" : "Live"}
          </div>
        </div>
      </div>

      <div style={{ padding: "24px 28px" }}>
        {error && (
          <div style={{ background: C.red + "22", border: `1px solid ${C.red}44`, borderRadius: 6, padding: "10px 16px", marginBottom: 20, fontSize: 13, color: C.red }}>
            {error}
          </div>
        )}

        {/* Row 1: Stat cards + Pie */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.2fr", gap: 16, marginBottom: 16 }}>
          <StatCard title="Health Score" value={summary ? `${summary.health_score}%` : null} sub="System health index" color={healthColor} />
          <StatCard
            title="Anomalies Detected"
            value={summary ? `${summary.anomalies_detected} / ${vaeAnomalies.length}` : null}
            sub="Isolation Forest / VAE-LSTM"
            color={summary?.anomalies_detected > 0 ? C.red : C.green}
            alert={summary?.anomalies_detected > 0 ? "Action required" : undefined}
          />
          <StatCard title="Anomaly Rate" value={summary ? `${summary.anomaly_rate}%` : null} sub="Isolation Forest · 5% contamination" color={anomalyRateColor} />
          <Panel title="Anomaly Distribution by Host">
            <PieChart width={220} height={130}>
              <Pie data={pieData} cx={70} cy={58} innerRadius={32} outerRadius={52} paddingAngle={2} dataKey="value">
                {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Legend layout="vertical" align="right" verticalAlign="middle" iconSize={8}
                formatter={(v) => <span style={{ fontSize: 10, color: C.textMuted }}>{v}</span>}
              />
            </PieChart>
          </Panel>
        </div>

        {/* Row 2: Charts */}
        <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 16, marginBottom: 16 }}>
          <Panel title="Anomaly Score Timeline">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid stroke={C.gridLine} strokeDasharray="4 4" />
                <XAxis dataKey="ts" tick={{ fill: C.textDim, fontSize: 10 }} tickLine={false} axisLine={{ stroke: C.panelBorder }} interval={20} />
                <YAxis tick={{ fill: C.textDim, fontSize: 10 }} tickLine={false} axisLine={false} width={40} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey="anomaly_score" stroke={C.yellow} strokeWidth={1.5} dot={false} name="Anomaly Score" />
                {chartData.filter(d => d.is_anomaly).map((d, i) => (
                  <ReferenceDot key={i} x={d.ts} y={d.anomaly_score} r={4} fill={C.accent} stroke="none" />
                ))}
              </LineChart>
            </ResponsiveContainer>
            <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 20, height: 2, background: C.yellow }} />
                <span style={{ fontSize: 11, color: C.textMuted }}>Anomaly Score</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.accent }} />
                <span style={{ fontSize: 11, color: C.textMuted }}>Anomaly Detected</span>
              </div>
            </div>
          </Panel>
          <Panel title="Log Events per Minute">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid stroke={C.gridLine} strokeDasharray="4 4" />
                <XAxis dataKey="ts" tick={{ fill: C.textDim, fontSize: 10 }} tickLine={false} axisLine={{ stroke: C.panelBorder }} interval={20} />
                <YAxis tick={{ fill: C.textDim, fontSize: 10 }} tickLine={false} axisLine={false} width={36} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey="log_event_count" stroke={C.purple} strokeWidth={1.5} dot={false} name="Log Events" />
              </LineChart>
            </ResponsiveContainer>
          </Panel>
        </div>

        {/* Isolation Forest Table */}
        <Panel title="Isolation Forest — Anomaly Events" style={{ marginBottom: 16 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.panelBorder}` }}>
                {["Timestamp", "Anomaly Score", "Log Events / min", "PC1", "PC2", "Status"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "6px 10px", color: C.textDim, fontWeight: 600, fontSize: 11, letterSpacing: "0.05em" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {anomalies.length === 0 && (
                <tr><td colSpan={6} style={{ padding: "20px 10px", color: C.textDim, textAlign: "center" }}>{loading ? "Loading..." : "No anomalies found"}</td></tr>
              )}
              {anomalies.slice(0, 15).map((a, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${C.gridLine}` }}
                  onMouseEnter={e => e.currentTarget.style.background = C.rowHover}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <td style={{ padding: "7px 10px", color: C.textMuted, fontFamily: "monospace", fontSize: 11 }}>{a.timestamp}</td>
                  <td style={{ padding: "7px 10px", color: C.accent, fontWeight: 600 }}>{a.anomaly_score?.toFixed(5) ?? "—"}</td>
                  <td style={{ padding: "7px 10px", color: C.textPrimary }}>{a.log_event_count ?? "—"}</td>
                  <td style={{ padding: "7px 10px", color: C.textMuted }}>{a.PC1?.toFixed(3) ?? "—"}</td>
                  <td style={{ padding: "7px 10px", color: C.textMuted }}>{a.PC2?.toFixed(3) ?? "—"}</td>
                  <td style={{ padding: "7px 10px" }}><Badge label="ANOMALY" color={C.red} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* VAE-LSTM Table */}
        <Panel title="VAE-LSTM — Anomaly Events" style={{ marginBottom: 16 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.panelBorder}` }}>
                {["Timestamp", "Reconstruction Error", "Log Events / min", "Status"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "6px 10px", color: C.textDim, fontWeight: 600, fontSize: 11, letterSpacing: "0.05em" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {vaeAnomalies.length === 0 && (
                <tr><td colSpan={4} style={{ padding: "20px 10px", color: C.textDim, textAlign: "center" }}>{loading ? "Loading..." : "No VAE anomalies found"}</td></tr>
              )}
              {vaeAnomalies.slice(0, 15).map((a, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${C.gridLine}` }}
                  onMouseEnter={e => e.currentTarget.style.background = C.rowHover}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <td style={{ padding: "7px 10px", color: C.textMuted, fontFamily: "monospace", fontSize: 11 }}>{a.timestamp}</td>
                  <td style={{ padding: "7px 10px", color: C.cyan, fontWeight: 600 }}>{a.vae_error?.toFixed(6) ?? "—"}</td>
                  <td style={{ padding: "7px 10px", color: C.textPrimary }}>{a.log_event_count ?? "—"}</td>
                  <td style={{ padding: "7px 10px" }}><Badge label="VAE ANOMALY" color={C.cyan} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Model Comparison */}
        <Panel title="Model Agreement — Isolation Forest vs VAE-LSTM" style={{ marginBottom: 16 }}>
          <ModelCompare />
        </Panel>

        {/* Live Monitor */}
        <Panel title="Live Anomaly Monitor — Microservice" style={{ marginBottom: 16 }}>
          <LiveMonitor />
        </Panel>

        {/* SHAP Explanation Panel */}
        <Panel title="SHAP — Fault Explanations" style={{ marginBottom: 16 }}>
          {explanations.length === 0 && (
            <div style={{ color: C.textDim, fontSize: 13, padding: "10px 0" }}>
              {loading ? "Loading..." : "No explanations found"}
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {explanations.slice(0, 8).map((e, i) => (
              <div key={i} style={{
                borderLeft: `3px solid ${C.accent}`, paddingLeft: 14,
                paddingTop: 8, paddingBottom: 8,
                background: C.accentSoft, borderRadius: "0 6px 6px 0",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontFamily: "monospace", fontSize: 11, color: C.textMuted }}>{e.timestamp?.slice(0, 16)}</span>
                  <span style={{ fontSize: 11, color: C.orange }}>Score: {e.anomaly_score?.toFixed(4)}</span>
                </div>
                <div style={{ fontSize: 12, color: C.textPrimary, marginBottom: 6 }}>{e.nl_explanation}</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                  <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: C.red + "22", color: C.red, border: `1px solid ${C.red}44` }}>
                    {e.top_feature}: {e.top_feature_pct}%
                  </span>
                  <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: C.yellow + "22", color: C.yellow, border: `1px solid ${C.yellow}44` }}>
                    {e.second_feature}: {e.second_feature_pct}%
                  </span>
                  <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: C.purple + "22", color: C.purple, border: `1px solid ${C.purple}44` }}>
                    Log burst: {e.log_event_count} events/min
                  </span>
                </div>
                {e.remediation && (
                  <div style={{ padding: "8px 10px", background: "rgba(0,0,0,0.3)", borderRadius: 4, fontSize: 11 }}>
                    <div style={{ color: C.orange, fontWeight: 600, marginBottom: 4 }}>🛠 {e.remediation.urgency}</div>
                    <div style={{ color: C.textDim, marginBottom: 4 }}>Recommended Actions:</div>
                    {e.remediation.steps.map((step, si) => (
                      <div key={si} style={{ color: C.textMuted, marginBottom: 2 }}>{si + 1}. {step}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Panel>

        {/* VAE-LSTM Explanations Panel */}
        <Panel title="VAE-LSTM — Temporal Anomaly Explanations" style={{ marginBottom: 16 }}>
          {vaeExplanations.length === 0 && (
            <div style={{ color: C.textDim, fontSize: 13, padding: "10px 0" }}>
              {loading ? "Loading..." : "No VAE explanations found"}
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {vaeExplanations.slice(0, 8).map((e, i) => (
              <div key={i} style={{
                borderLeft: `3px solid ${C.cyan}`, paddingLeft: 14,
                paddingTop: 8, paddingBottom: 8,
                background: "rgba(76,201,240,0.06)", borderRadius: "0 6px 6px 0",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontFamily: "monospace", fontSize: 11, color: C.textMuted }}>{e.timestamp?.slice(0, 16)}</span>
                  <span style={{ fontSize: 11, color: C.cyan }}>Recon Error: {e.vae_error?.toFixed(5)}</span>
                </div>
                <div style={{ fontSize: 12, color: C.textPrimary, marginBottom: 6 }}>{e.nl_explanation}</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: C.cyan + "22", color: C.cyan, border: `1px solid ${C.cyan}44` }}>
                    {e.top_feature}: {e.top_feature_pct}%
                  </span>
                  <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: C.yellow + "22", color: C.yellow, border: `1px solid ${C.yellow}44` }}>
                    {e.second_feature}: {e.second_feature_pct}%
                  </span>
                  <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: C.purple + "22", color: C.purple, border: `1px solid ${C.purple}44` }}>
                    Log activity: {e.log_event_count} events/min
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {/* Row 4: Worst anomaly + System info */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <Panel title="Worst Anomaly Event">
            {summary?.worst_anomaly_time ? (
              <div>
                <div style={{ fontSize: 13, color: C.textMuted, marginBottom: 6 }}>Peak anomaly detected at:</div>
                <div style={{ fontFamily: "monospace", fontSize: 14, color: C.accent, fontWeight: 600 }}>{summary.worst_anomaly_time}</div>
                <div style={{ marginTop: 12, fontSize: 12, color: C.textDim }}>
                  Investigate metric PC1 and log burst around this timestamp for root cause.
                </div>
              </div>
            ) : (
              <div style={{ color: C.textDim, fontSize: 13 }}>No data</div>
            )}
          </Panel>
          <Panel title="System Info">
            <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
              {[
                ["Dataset",       "LO2 · Light-OAuth2"],
                ["Hosts",         "wally113, 117, 122, 123, 124"],
                ["Detection",     "Isolation Forest + VAE-LSTM"],
                ["Log Parser",    "Drain3 · TemplateMiner"],
                ["Preprocessing", "StandardScaler + PCA (5 components)"],
                ["Window Size",   "1 minute bins"],
              ].map(([k, v]) => (
                <tr key={k} style={{ borderBottom: `1px solid ${C.gridLine}` }}>
                  <td style={{ padding: "5px 0", color: C.textDim, width: 130 }}>{k}</td>
                  <td style={{ padding: "5px 0", color: C.textPrimary }}>{v}</td>
                </tr>
              ))}
            </table>
          </Panel>
        </div>
      </div>
    </div>
  );
}