"use client";

import React, { useState } from "react";
import { ArrowUpDown } from "lucide-react";

interface Metric {
  value: any;
  source: string;
  confidence: number;
}

interface MetricsTableProps {
  metrics: Record<string, Metric>;
}

export default function MetricsTable({ metrics = {} }: MetricsTableProps) {
  const [sortKey, setSortKey] = useState<"name" | "confidence">("confidence");
  const [sortAsc, setSortAsc] = useState(true);

  const entries = Object.entries(metrics).map(([name, data]) => ({
    name,
    ...data,
  }));

  const sortedEntries = entries.sort((a, b) => {
    let comparison = 0;
    if (sortKey === "name") {
      comparison = a.name.localeCompare(b.name);
    } else {
      comparison = a.confidence - b.confidence;
    }
    return sortAsc ? comparison : -comparison;
  });

  const handleSort = (key: "name" | "confidence") => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return "bg-[#10b981]";
    if (confidence >= 0.6) return "bg-[#f59e0b]";
    return "bg-[#f43f5e]";
  };

  if (entries.length === 0) {
    return <div className="text-zinc-500 text-sm py-4 font-sans">No metrics available.</div>;
  }

  return (
    <div className="overflow-x-auto rounded-md border border-[#00e5ff15] terminal-card">
      <table className="w-full text-sm text-left">
        <thead className="text-[10px] text-[#00e5ff80] uppercase tracking-[0.1em] border-b border-[#00e5ff15] bg-[#00e5ff05]">
          <tr>
            <th
              className="px-6 py-4 cursor-pointer hover:text-[#00e5ff] transition-colors"
              onClick={() => handleSort("name")}
            >
              <div className="flex items-center gap-1 font-sans">
                Metric Name
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>
            <th className="px-6 py-4 font-sans">Value</th>
            <th className="px-6 py-4 font-sans">Source</th>
            <th
              className="px-6 py-4 cursor-pointer hover:text-[#00e5ff] transition-colors"
              onClick={() => handleSort("confidence")}
            >
              <div className="flex items-center gap-1 font-sans">
                Confidence
                <ArrowUpDown className="w-3 h-3" />
              </div>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#00e5ff05]">
          {sortedEntries.map((row, idx) => (
            <tr
              key={row.name}
              className={`transition-colors ${
                idx % 2 === 0 ? "bg-[#00e5ff02]" : "bg-transparent"
              } hover:bg-[#00e5ff08]`}
            >
              <td className="px-6 py-4 font-medium text-zinc-300 font-sans">{row.name}</td>
              <td className="px-6 py-4 font-mono text-[#00e5ff]">{String(row.value)}</td>
              <td className="px-6 py-4 text-zinc-500 text-[10px] uppercase tracking-widest font-sans">{row.source}</td>
              <td className="px-6 py-4 min-w-[140px]">
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-1.5 bg-[#ffffff05] rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-1000 ${getConfidenceColor(row.confidence)}`}
                      style={{ width: `${row.confidence * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-[10px] text-zinc-400 w-8 text-right">
                    {Math.round(row.confidence * 100)}%
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
