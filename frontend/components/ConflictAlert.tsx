import React from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";

interface Conflict {
  metric_name: string;
  source_1_value: any;
  source_2_value: any;
  description: string;
  resolution_rationale: string;
}

interface ConflictAlertProps {
  conflicts?: Conflict[];
}

export default function ConflictAlert({ conflicts = [] }: ConflictAlertProps) {
  if (conflicts.length === 0) {
    return (
      <div className="flex items-center gap-2 p-4 bg-[#10b98108] border border-[#10b98120] rounded-md text-[#10b981] text-xs font-sans">
        <CheckCircle2 className="w-4 h-4" />
        <span className="font-medium tracking-wide uppercase">No Data Conflicts Detected</span>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-5 bg-[#f59e0b05] border border-[#f59e0b20] rounded-md text-[#f59e0b] font-sans">
      <div className="flex items-center gap-2 font-semibold text-sm uppercase tracking-wider">
        <AlertCircle className="w-5 h-5" />
        <span>Data Conflicts Detected ({conflicts.length})</span>
      </div>
      <ul className="space-y-4 mt-4">
        {conflicts.map((c, i) => (
          <li key={i} className="bg-[#f59e0b08] p-4 rounded border border-[#f59e0b15]">
            <div className="font-bold text-[#f59e0b] uppercase text-[10px] tracking-widest mb-2 border-b border-[#f59e0b20] pb-1 w-fit">{c.metric_name}</div>
            <div className="mt-2 text-xs text-[#f59e0b90] leading-relaxed">
              <span className="font-bold text-[#f59e0b] mr-2">CONFLICT:</span> {c.description}
            </div>
            <div className="mt-2 text-xs text-[#f59e0b90] leading-relaxed">
              <span className="font-bold text-[#f59e0b] mr-2">RESOLUTION:</span> {c.resolution_rationale}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
