"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Terminal } from "lucide-react";

export default function InputDashboard() {
  const [query, setQuery] = useState("");
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleSubmit() {
    // Prevent double submission
    if (loading) return;
    setLoading(true);
    setError("");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, ticker: ticker.toUpperCase() }),
      });

      const result = await res.json();

      // Check envelope
      if (!result.success || !result.data?.job_id) {
        throw new Error(result.error || "No job_id returned from server");
      }

      // Navigate with REAL job_id
      router.push(`/status/${result.data.job_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to start research. Is the backend running?");
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] w-full">
      <div className="w-full max-w-4xl space-y-12">
        <div className="text-center space-y-4">
          <h1 className="text-6xl md:text-7xl font-extralight tracking-[0.3em] text-[#fafafa] uppercase drop-shadow-[0_0_15px_rgba(0,229,255,0.3)]">
            RESEARCH TERMINAL
          </h1>
        </div>

        <div className="terminal-card p-2 rounded-lg bg-[#0f1729cc]">
          <div className="flex flex-col md:flex-row gap-2">
            <div className="relative group">
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="TICKER"
                className="w-full md:w-32 px-4 py-4 bg-[#070b14] border border-[#00e5ff20] rounded text-[#00e5ff] placeholder:text-[#00e5ff40] focus:outline-none focus:border-[#00e5ff80] font-mono transition-all text-center"
                disabled={loading}
                maxLength={5}
              />
              <div className="absolute -top-2 left-2 bg-[#0a0e1a] px-1 text-[8px] text-[#00e5ff60] tracking-widest font-mono">
                ASSET_ID
              </div>
            </div>

            <div className="flex-1 relative group">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="EXECUTE RESEARCH QUERY..."
                className="w-full px-6 py-4 bg-[#070b14] border border-[#00e5ff20] rounded text-[#fafafa] placeholder:text-[#ffffff20] focus:outline-none focus:border-[#00e5ff80] transition-all"
                disabled={loading}
              />
              <div className="absolute -top-2 left-4 bg-[#0a0e1a] px-1 text-[8px] text-[#00e5ff60] tracking-widest font-mono">
                QUERY_PARAM
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading || !ticker || !query}
              className="px-8 py-4 bg-transparent border border-[#00e5ff40] text-[#00e5ff] rounded hover:bg-[#00e5ff10] transition-all flex items-center justify-center gap-2 font-semibold tracking-wider disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Initializing...</span>
                </>
              ) : (
                <>
                  <Terminal className="w-4 h-4" />
                  <span>Start Research</span>
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <p style={{ color: "#f43f5e", fontSize: "14px", marginTop: "8px", textAlign: "center" }}>
            {error}
          </p>
        )}

        <div className="flex flex-col items-center gap-4 pt-12">
          <div className="flex items-center gap-3 text-[10px] text-zinc-500 font-mono tracking-widest uppercase">
            <span className="status-pulse"></span>
            <span>System Online • 12 Data Sources Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
