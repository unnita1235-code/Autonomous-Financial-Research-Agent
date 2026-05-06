"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

type JobStatus = "queued" | "running" | "complete" | "failed";

interface StatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  message?: string;
  error?: string;
}

export default function StatusPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const [status, setStatus] = useState<JobStatus>("queued");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("INITIALIZING SYSTEM UPLINK...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const fetchStatus = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/status/${jobId}`);
        const data = await res.json();

        if (!res.ok) throw new Error(data.message || "TELEMETRY FAILURE");

        const jobStatus: StatusResponse = data.data;
        setStatus(jobStatus.status);
        if (jobStatus.progress !== undefined) setProgress(jobStatus.progress);
        if (jobStatus.message) setMessage(jobStatus.message.toUpperCase());

        if (jobStatus.status === "complete") {
          router.push(`/report/${jobId}`);
        } else if (jobStatus.status === "failed") {
          setError(jobStatus.error || "CRITICAL JOB FAILURE");
        }
      } catch (err: any) {
        console.error("Status fetch error:", err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [jobId, router]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] w-full">
      <div className="w-full max-w-xl space-y-8 terminal-card p-8 rounded-lg">
        <div className="space-y-2 text-left border-b border-[#00e5ff15] pb-4">
          <h1 className="text-xl font-light tracking-[0.2em] text-[#fafafa] uppercase">
            RESEARCH IN PROGRESS
          </h1>
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-[#00e5ff60] font-mono tracking-widest">SESSION_ID: {jobId}</span>
            <span className="text-[10px] text-[#00e5ff60] font-mono tracking-widest uppercase">{status}</span>
          </div>
        </div>

        <div className="space-y-6">
          {error ? (
            <div className="space-y-4">
              <div className="p-4 bg-[#f43f5e05] border border-[#f43f5e20] rounded text-[#f43f5e] font-mono text-xs tracking-wider">
                SYSTEM_ERROR: {error}
              </div>
              <button
                onClick={() => router.push("/")}
                className="w-full py-3 border border-[#f43f5e40] text-[#f43f5e] rounded hover:bg-[#f43f5e10] transition-all text-xs tracking-widest uppercase font-bold"
              >
                ABORT AND RESTART
              </button>
            </div>
          ) : (
            <div className="space-y-8">
              <div className="relative h-1 w-full bg-[#ffffff05] rounded-full overflow-hidden">
                <div
                  className="absolute top-0 left-0 h-full bg-[#00e5ff] transition-all duration-1000 shadow-[0_0_10px_rgba(0,229,255,0.5)]"
                  style={{ width: `${Math.max(progress, 5)}%` }}
                />
              </div>
              
              <div className="flex items-center gap-4 text-[#00e5ff] animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs font-mono tracking-[0.2em] uppercase">
                  {message}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
