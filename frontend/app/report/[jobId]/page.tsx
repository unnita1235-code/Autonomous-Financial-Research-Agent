"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronRight, Copy, Check, Terminal, ExternalLink } from "lucide-react";
import MetricsTable from "@/components/MetricsTable";
import ConflictAlert from "@/components/ConflictAlert";

interface ReportData {
  report_id: string;
  ticker: string;
  query: string;
  status: string;
  synthesis_quality: number;
  markdown: string;
  sections: {
    executive_summary: { content: string; data_quality: string };
    financial_metrics: { content: string; rows: any[]; data_quality: string };
    management_insights: { content: string; data_quality: string };
    risk_assessment: { content: string; data_quality: string };
    data_conflicts: { content: string; conflict_items: any[]; narrative?: string; data_quality: string };
    final_verdict: { content: string; signal: string; reason: string; data_quality: string; confidence: string };
  };
}

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    executive_summary: true,
    business_overview: false,
    metrics_and_conflicts: true,
    financial_performance: false,
    risk_factors: false,
    investment_verdict: true,
  });

  useEffect(() => {
    if (!jobId) return;
    const fetchReport = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/report/${jobId}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || "DATA RETRIEVAL ERROR");
        setReport(data.data);
      } catch (err: any) {
        setError(err.message || "REPORT ACCESS DENIED");
      }
    };
    fetchReport();
  }, [jobId]);

  const copyToClipboard = () => {
    if (!report) return;
    navigator.clipboard.writeText(report.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const getVerdictStyle = (verdict: string = "") => {
    const v = verdict.toLowerCase();
    if (v.includes("buy") || v.includes("positive")) return "text-[#10b981] border-[#10b98140] bg-[#10b98110]";
    if (v.includes("sell") || v.includes("negative") || v.includes("caution") || v.includes("risk")) return "text-[#f43f5e] border-[#f43f5e40] bg-[#f43f5e10]";
    return "text-[#f59e0b] border-[#f59e0b40] bg-[#f59e0b10]";
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] w-full">
        <div className="terminal-card p-8 rounded-lg border-[#f43f5e40] space-y-4 text-center max-w-md">
          <Terminal className="w-8 h-8 text-[#f43f5e] mx-auto" />
          <h2 className="text-xl font-bold text-[#f43f5e] tracking-widest uppercase">ACCESS DENIED</h2>
          <p className="text-zinc-500 font-mono text-xs uppercase">{error}</p>
          <button onClick={() => router.push("/")} className="px-4 py-2 border border-[#f43f5e40] text-[#f43f5e] rounded text-xs uppercase font-bold hover:bg-[#f43f5e10] transition-all">RESTART TERMINAL</button>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const reportSections = [
    { id: "executive_summary", title: "EXECUTIVE SUMMARY", content: report.sections.executive_summary?.content || "" },
    { id: "management_insights", title: "MANAGEMENT INSIGHTS", content: report.sections.management_insights?.content || "" },
    { id: "financial_performance", title: "FINANCIAL PERFORMANCE", content: report.sections.financial_metrics?.content || "" },
    { id: "risk_factors", title: "RISK EXPOSURE", content: report.sections.risk_assessment?.content || "" },
    { id: "investment_verdict", title: "INVESTMENT VERDICT", content: report.sections.final_verdict?.content || "" },
  ];

  const qualityScore = Math.round(report.synthesis_quality * 100);
  const strokeDasharray = 2 * Math.PI * 45;
  const strokeDashoffset = strokeDasharray * (1 - qualityScore / 100);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-32 animate-in fade-in duration-700">
      {/* HUD Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-[#00e5ff15] pb-6">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="px-2 py-1 bg-[#00e5ff10] border border-[#00e5ff30] text-[#00e5ff] text-[10px] font-mono tracking-widest">ANALYSIS_REPORT</span>
            <span className="text-zinc-500 font-mono text-[10px] tracking-widest">ID: {jobId.slice(0, 8)}</span>
          </div>
          <h1 className="text-5xl font-light tracking-[0.1em] text-[#fafafa] uppercase">
            {report.ticker} <span className="text-[#00e5ff60]">TERMINAL</span>
          </h1>
          <p className="text-[#00e5ff80] max-w-2xl text-xs font-mono uppercase tracking-wider italic">
            &gt; {report.query}
          </p>
        </div>

        <div className="flex items-center gap-6">
          <div className="relative w-24 h-24">
            <svg className="w-full h-full -rotate-90">
              <circle cx="48" cy="48" r="45" fill="transparent" stroke="#ffffff05" strokeWidth="4" />
              <circle 
                cx="48" cy="48" r="45" fill="transparent" stroke="#00e5ff" strokeWidth="4" 
                strokeDasharray={strokeDasharray} strokeDashoffset={strokeDashoffset}
                strokeLinecap="round" className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-mono text-[#00e5ff] leading-none">{qualityScore}</span>
              <span className="text-[8px] text-[#00e5ff60] font-mono tracking-tighter">QUALITY</span>
            </div>
          </div>
          
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-2 px-4 py-2 border border-[#00e5ff30] text-[#00e5ff60] hover:text-[#00e5ff] hover:border-[#00e5ff] rounded-md transition-all text-[10px] font-bold uppercase tracking-widest"
          >
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied ? "COPIED" : "MARKDOWN"}
          </button>
        </div>
      </div>

      {/* Main Signal Badge */}
      <div className={`p-6 rounded-md border-l-4 ${getVerdictStyle(report.sections.final_verdict?.signal)} transition-all shadow-[0_0_20px_rgba(0,0,0,0.3)]`}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-2 h-2 rounded-full bg-current animate-pulse"></div>
          <h2 className="text-xs font-bold uppercase tracking-[0.3em] opacity-80">FINAL_INVESTMENT_SIGNAL</h2>
        </div>
        <div className="prose prose-invert max-w-none prose-sm font-sans leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {report.sections.final_verdict?.content || "SIGNAL_PENDING"}
          </ReactMarkdown>
        </div>
      </div>

      {/* HUD Sections */}
      <div className="grid grid-cols-1 gap-6">
        {reportSections.map((section) => (
          <div key={section.id} className="terminal-card rounded-md overflow-hidden border-l-2 border-[#00e5ff20] hover:border-[#00e5ff80] transition-all">
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full flex items-center justify-between p-5 bg-[#ffffff02] hover:bg-[#ffffff05] transition-colors group"
            >
              <div className="flex items-center gap-4">
                <div className={`w-1 h-4 bg-[#00e5ff40] transition-all ${expandedSections[section.id] ? "h-6 bg-[#00e5ff]" : ""}`}></div>
                <h2 className="text-xs font-bold text-zinc-300 tracking-[0.2em] uppercase group-hover:text-[#00e5ff] transition-colors">{section.title}</h2>
              </div>
              {expandedSections[section.id] ? (
                <ChevronDown className="w-4 h-4 text-zinc-600 group-hover:text-[#00e5ff]" />
              ) : (
                <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-[#00e5ff]" />
              )}
            </button>
            {expandedSections[section.id] && (
              <div className="p-8 pt-2 border-t border-[#00e5ff05] prose prose-invert max-w-none prose-zinc prose-sm font-sans animate-in slide-in-from-top-2 duration-300">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {section.content || "*DATA UNAVAILABLE*"}
                </ReactMarkdown>
              </div>
            )}
          </div>
        ))}

        {/* Structured Data HUD */}
        <div className="terminal-card rounded-md overflow-hidden border-l-2 border-[#00e5ff20]">
          <button
            onClick={() => toggleSection("metrics_and_conflicts")}
            className="w-full flex items-center justify-between p-5 bg-[#ffffff02] hover:bg-[#ffffff05] transition-colors group"
          >
            <div className="flex items-center gap-4">
              <div className={`w-1 h-4 bg-[#00e5ff40] transition-all ${expandedSections["metrics_and_conflicts"] ? "h-6 bg-[#00e5ff]" : ""}`}></div>
              <h2 className="text-xs font-bold text-zinc-300 tracking-[0.2em] uppercase group-hover:text-[#00e5ff] transition-colors">DATA_SYNTHESIS_METRICS</h2>
            </div>
            {expandedSections["metrics_and_conflicts"] ? (
              <ChevronDown className="w-4 h-4 text-zinc-600 group-hover:text-[#00e5ff]" />
            ) : (
              <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-[#00e5ff]" />
            )}
          </button>
          {expandedSections["metrics_and_conflicts"] && (
            <div className="p-8 pt-2 border-t border-[#00e5ff05] space-y-8 animate-in slide-in-from-top-2 duration-300">
              <ConflictAlert conflicts={report.sections.data_conflicts?.conflict_items || []} />
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Terminal className="w-3 h-3 text-[#00e5ff80]" />
                  <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">
                    SYNTHESIZED_FINANCIAL_METRICS
                  </h3>
                </div>
                <MetricsTable metrics={report.sections.financial_metrics?.rows || []} />
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Footer Info */}
      <div className="flex justify-between items-center text-[8px] font-mono text-zinc-700 tracking-[0.3em] uppercase pt-12">
        <span>&copy; 2026 AGENT_RESEARCH_UPLINK</span>
        <div className="flex gap-4">
          <span>SEC_EDGAR_READY</span>
          <span>ALPHA_VANTAGE_SYNC</span>
          <span>TRANSCRIPT_RECON_ACTIVE</span>
        </div>
      </div>
    </div>
  );
}
