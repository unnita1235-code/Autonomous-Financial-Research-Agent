try:
    from prometheus_client import Counter, Histogram, Gauge

    research_jobs_total = Counter("research_jobs_total", "Total research jobs", ["status"])
    tool_calls_total    = Counter("tool_calls_total", "Total tool calls", ["tool", "success"])
    pipeline_duration   = Histogram("pipeline_duration_seconds", "Pipeline time",
                                     buckets=[30, 60, 90, 120, 150, 180, 300])
    synthesis_quality   = Histogram("synthesis_quality_score", "Synthesis quality",
                                     buckets=[0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 1.0])
    active_jobs         = Gauge("active_jobs_current", "Jobs currently running")
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    class _Noop:
        def labels(self, **kw): return self
        def inc(self): pass
        def observe(self, v): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    research_jobs_total = _Noop()
    tool_calls_total    = _Noop()
    pipeline_duration   = _Noop()
    synthesis_quality   = _Noop()
    active_jobs         = _Noop()
