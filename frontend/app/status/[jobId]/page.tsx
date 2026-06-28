'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function StatusPage() {
  const params = useParams();
  const jobId = params.jobId as string; // matches folder name [jobId]
  const router = useRouter();

  const [status, setStatus] = useState('queued');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!jobId || jobId === 'undefined') {
      setError('Invalid job ID. Please go back and try again.');
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    let active = true; // prevents state updates after unmount

    const poll = async () => {
      try {
        const res = await fetch(`${apiUrl}/status/${jobId}`);
        const result = await res.json();

        if (!active) return;

        if (result.success && result.data) {
          setStatus(result.data.status);

          if (result.data.status === 'complete') {
            router.push(`/report/${jobId}`);
            return; // stop polling
          }

          if (result.data.status === 'failed') {
            setError(result.error || result.data.error || 'Research pipeline failed.');
            return; // stop polling
          }
        } else {
          setError(result.error || 'Unexpected response from server');
          return;
        }
      } catch (err: any) {
        if (!active) return;
        // Network error — don't stop polling, just log it
        console.warn('Poll failed, retrying...', err.message);
      }

      // Schedule next poll only if still active and not done
      if (active) {
        setTimeout(poll, 15000); // 15 seconds to avoid rate limits
      }
    };

    // Start first poll after 3 seconds (give backend time to start)
    const initialTimeout = setTimeout(poll, 3000);

    return () => {
      active = false;
      clearTimeout(initialTimeout);
    };
  }, [jobId, router]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] w-full p-4">
      <div className="w-full max-w-xl space-y-8 terminal-card p-8 rounded-lg border border-[#00e5ff15] bg-[#0a0a0a]">
        <div className="space-y-2 text-left border-b border-[#00e5ff15] pb-4">
          <h1 className="text-xl font-light tracking-[0.2em] text-[#fafafa] uppercase">
            RESEARCH_STATUS
          </h1>
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-[#00e5ff60] font-mono tracking-widest">
              JOB_ID: {jobId}
            </span>
            <span className={`text-[10px] font-mono tracking-widest uppercase ${status === 'failed' ? 'text-red-500' : 'text-[#00e5ff]'}`}>
              {status}
            </span>
          </div>
        </div>

        <div className="space-y-6">
          {error ? (
            <div className="space-y-6">
              <div className="p-4 bg-red-500/5 border border-red-500/20 rounded text-red-400 font-mono text-xs tracking-wider leading-relaxed">
                <div className="font-bold mb-1 uppercase tracking-tighter">SYSTEM_ERROR_LOG:</div>
                {error}
              </div>
              <Link
                href="/"
                className="flex items-center justify-center gap-2 w-full py-3 border border-red-500/40 text-red-500 rounded hover:bg-red-500/10 transition-all text-xs tracking-widest uppercase font-bold"
              >
                <ArrowLeft className="w-3 h-3" />
                Go Back to Research
              </Link>
            </div>
          ) : (
            <div className="space-y-8">
              {/* Progress Indicator */}
              <div className="relative h-1 w-full bg-white/5 rounded-full overflow-hidden">
                <div
                  className={`absolute top-0 left-0 h-full bg-[#00e5ff] transition-all duration-1000 shadow-[0_0_10px_rgba(0,229,255,0.5)]`}
                  style={{ 
                    width: status === 'queued' ? '15%' : status === 'running' ? '60%' : '5%' 
                  }}
                />
              </div>
              
              <div className="flex items-center gap-4 text-[#00e5ff]">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs font-mono tracking-[0.2em] uppercase animate-pulse">
                  {status === 'queued' ? 'AWAITING_RESOURCES...' : 'ANALYZING_FINANCIAL_DATA...'}
                </span>
              </div>

              <Link
                href="/"
                className="flex items-center justify-center gap-2 text-[#00e5ff60] hover:text-[#00e5ff] transition-colors text-[10px] font-mono tracking-widest uppercase mt-4"
              >
                <ArrowLeft className="w-3 h-3" />
                Go Back
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
