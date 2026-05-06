"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronRight, Copy, Check, Terminal, ArrowLeft, Loader2 } from "lucide-react";
import ConflictAlert from "@/components/ConflictAlert";

export default function ReportPage() {
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    executive_summary: true,
    financial_metrics: true,
    management_insights: false,
    risk_assessment: false,
    data_conflicts: true,
    final_verdict: true,
  });

  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  useEffect(() => {
    if (!jobId || jobId === "undefined") {
      setError("Invalid report ID");
      setLoading(false);
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/report/${jobId}`)
      .then((res) => res.json())
      .then((result) => {
        if (result.success && result.data) {
          setReport(result.data);
        } else {
          setError(result.error || "Failed to load report");
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(`Network error: ${err.message}`);
        setLoading(false);
      });
  }, [jobId]);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(report?.markdown || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  function renderConfidenceBadge(conf: string) {
    const num = parseInt(conf);
    let color = "#f43f5e"; // red
    if (num >= 80) color = "#10b981"; // green
    else if (num >= 60) color = "#f59e0b"; // amber
    return (
      <span
        style={{
          background: color,
          color: "#fff",
          padding: "2px 8px",
          borderRadius: "4px",
          fontSize: "12px",
          fontFamily: "JetBrains Mono, monospace",
        }}
      >
        {conf}
      </span>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Loader2 className="w-12 h-12 text-[#00e5ff] animate-spin" />
        <p className="text-[#00e5ff] font-mono text-xs uppercase tracking-widest">Initialising neural link...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-4 text-center">
        <div className="max-w-md p-8 border border-red-500/20 bg-red-500/5 rounded-lg space-y-6">
          <Terminal className="w-12 h-12 text-red-500 mx-auto" />
          <h2 className="text-2xl font-bold text-red-500 tracking-tighter uppercase">ACCESS_DENIED</h2>
          <p className="text-zinc-400 font-mono text-sm">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 px-6 py-3 bg-red-500 text-white rounded-md font-bold uppercase text-xs tracking-widest hover:bg-red-600 transition-all mx-auto"
          >
            <ArrowLeft className="w-4 h-4" /> Go Back
          </button>
        </div>
      </div>
    );
  }

  const sections = report?.sections || report?.report_components || {};
  const synthesisQuality = report?.synthesis_quality || 0;
  const verdict = sections?.final_verdict;
  const metrics = sections?.financial_metrics;
  const metricsRows = metrics?.rows || metrics?.metrics || [];

  const qualityColor =
    synthesisQuality > 0.8 ? "#10b981" : synthesisQuality > 0.6 ? "#f59e0b" : "#f43f5e";

  const getVerdictBg = (signal: string) => {
    switch (signal) {
      case "Positive":
        return "bg-[#10b98120] border-[#10b98140] text-[#10b981]";
      case "Neutral":
        return "bg-[#f59e0b20] border-[#f59e0b40] text-[#f59e0b]";
      case "Caution":
        return "bg-[#f43f5e20] border-[#f43f5e40] text-[#f43f5e]";
      case "Insufficient Data":
        return "bg-zinc-500/20 border-zinc-500/40 text-zinc-400";
      default:
        return "bg-zinc-800 border-zinc-700 text-zinc-400";
    }
  };

  const sectionOrder = [
    { id: "executive_summary", title: "Executive Summary" },
    { id: "financial_metrics", title: "Financial Metrics" },
    { id: "management_insights", title: "Management Insights" },
    { id: "risk_assessment", title: "Risk Assessment" },
    { id: "data_conflicts", title: "Data Conflicts" },
    { id: "final_verdict", title: "Final Verdict" },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 space-y-12 animate-in fade-in duration-1000">
      {/* Header HUD */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8 border-b border-[#00e5ff10] pb-10">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 bg-[#00e5ff10] border border-[#00e5ff20] text-[#00e5ff] text-[10px] font-mono tracking-widest uppercase">
              Research_Report
            </span>
            <span className="text-zinc-600 font-mono text-[10px] tracking-widest">
              ID: {report?.report_id?.slice(0, 8) || "N/A"}
            </span>
          </div>
          <h1 className="text-6xl font-black tracking-tighter text-white">
            {report?.ticker} <span className="text-zinc-800">ANALYSIS</span>
          </h1>
          <p className="text-zinc-500 max-w-2xl font-mono text-xs uppercase italic tracking-tight">
            &gt; {report?.query}
          </p>
        </div>

        <div className="flex items-center gap-8 bg-zinc-900/50 p-6 rounded-2xl border border-white/5">
          <div className="text-center">
            <div
              className="text-4xl font-black mb-1"
              style={{ color: qualityColor }}
            >
              {Math.round(synthesisQuality * 100)}%
            </div>
            <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
              Synthesis Quality
            </div>
          </div>

          <button
            onClick={copyToClipboard}
            className="flex items-center gap-2 px-5 py-3 border border-zinc-800 text-zinc-400 hover:text-white hover:border-[#00e5ff] hover:bg-[#00e5ff10] rounded-xl transition-all text-xs font-bold uppercase tracking-widest"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? "Copied" : "Copy Markdown"}
          </button>
        </div>
      </div>

      {/* Final Verdict Highlight */}
      <div className={`p-8 rounded-2xl border ${getVerdictBg(verdict?.signal)} shadow-2xl transition-all`}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
            <h2 className="text-sm font-bold uppercase tracking-[0.2em]">Final Verdict: {verdict?.signal || "N/A"}</h2>
          </div>
          {verdict?.confidence && (
            <div className="text-xs font-mono opacity-60">Confidence: {verdict.confidence}</div>
          )}
        </div>
        <div className="prose prose-invert max-w-none prose-sm leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {verdict?.content || "No verdict content available."}
          </ReactMarkdown>
        </div>
      </div>

      {/* Sections Grid */}
      <div className="space-y-6">
        {sectionOrder.map((sectionInfo) => {
          const sectionData = sections[sectionInfo.id];
          if (!sectionData) return null;

          const isExpanded = expandedSections[sectionInfo.id];

          return (
            <div
              key={sectionInfo.id}
              className="bg-zinc-900/30 border border-white/5 rounded-2xl overflow-hidden hover:border-white/10 transition-all"
            >
              <button
                onClick={() => toggleSection(sectionInfo.id)}
                className="w-full flex items-center justify-between p-6 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-1 h-5 rounded-full transition-all ${isExpanded ? "bg-[#00e5ff]" : "bg-zinc-700"}`} />
                  <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-widest">{sectionInfo.title}</h3>
                </div>
                <div className="flex items-center gap-4">
                  {sectionData.data_quality && (
                    <span className="text-[10px] font-mono px-2 py-1 bg-zinc-800 rounded border border-zinc-700 text-zinc-500 uppercase">
                      Quality: {sectionData.data_quality}
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-zinc-600" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-zinc-600" />
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="p-8 pt-0 border-t border-white/5 animate-in slide-in-from-top-2 duration-300">
                  {sectionInfo.id === "financial_metrics" && metricsRows.length > 0 && (
                    <div className="mb-8 overflow-x-auto">
                      <table className="w-full text-left border-collapse min-w-[600px]">
                        <thead>
                          <tr className="border-b border-white/10">
                            <th className="py-4 text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Metric</th>
                            <th className="py-4 text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Value</th>
                            <th className="py-4 text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Source</th>
                            <th className="py-4 text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Confidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {metricsRows.map((row: any, i: number) => (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                              <td className="py-4 text-sm text-zinc-300 font-medium">{row.metric}</td>
                              <td className="py-4 text-sm text-[#00e5ff] font-mono">{row.value}</td>
                              <td className="py-4 text-xs text-zinc-500">{row.source}</td>
                              <td className="py-4">{renderConfidenceBadge(row.confidence)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {sectionInfo.id === "data_conflicts" && sectionData.conflict_items?.length > 0 && (
                    <div className="mb-6">
                      <ConflictAlert conflicts={sectionData.conflict_items} />
                    </div>
                  )}

                  <div className="prose prose-invert max-w-none prose-sm prose-zinc leading-loose">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {sectionData.content || "*No detailed content provided for this section.*"}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="pt-20 pb-10 flex justify-between items-center border-t border-white/5 text-[10px] font-mono text-zinc-700 uppercase tracking-[0.4em]">
        <span>&copy; 2026 AUTONOMOUS_FINANCIAL_RESEARCH</span>
        <div className="flex gap-8">
          <span>SEC_EDGAR_VERIFIED</span>
          <span>MULTI_SOURCE_SYNTHESIS</span>
        </div>
      </div>
    </div>
  );
}
