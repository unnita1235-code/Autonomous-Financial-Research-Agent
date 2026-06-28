"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface Row { metric: string; value: string; source: string; confidence: string; }
interface Props { rows: Row[]; }

export default function FinancialChart({ rows }: Props) {
  const data = rows
    .filter(r => r.metric !== "Sentiment Score" && r.metric !== "Eps")
    .map(r => {
      const clean = r.value.replace(/[$,%]/g, "");
      const num = parseFloat(clean);
      const mult = r.value.includes("B") ? 1e9 : r.value.includes("M") ? 1e6 : r.value.includes("K") ? 1e3 : 1;
      return { name: r.metric, value: isNaN(num) ? 0 : +(((num * mult) / 1e9).toFixed(1)) };
    })
    .filter(r => r.value > 0);

  if (data.length === 0) return null;

  return (
    <div style={{ width: "100%", height: 180, margin: "12px 0 20px" }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}B`} width={44} />
          <Tooltip
            formatter={(v: number) => [`$${v}B`, "Value"]}
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
          />
          <Bar dataKey="value" fill="#00e5ff" radius={[4, 4, 0, 0]} maxBarSize={60} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
