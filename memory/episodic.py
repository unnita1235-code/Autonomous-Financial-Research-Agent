"""
Episodic Memory — Layer 3 of the Three-Layer Memory Architecture.
Records structured episodes from each research run to enable learning.
Tracks: which tools worked, which strategies were effective, error patterns.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

EPISODIC_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "episodic_memory.json")


class EpisodicMemory:
    def __init__(self, filepath: str = EPISODIC_FILE):
        self.filepath = os.path.abspath(filepath)
        self.episodes: List[Dict] = self._load()
    
    def _load(self) -> List[Dict]:
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            pass
        return []
    
    def _save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.episodes, f, indent=2, default=str)
    
    def record_episode(self, episode_data: Dict) -> Dict:
        """Record a completed research episode."""
        episode = {
            "episode_id": f"ep_{len(self.episodes) + 1:04d}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": episode_data.get("query", ""),
            "query_type": episode_data.get("query_type", "general"),
            "tools_used": episode_data.get("tools_used", []),
            "tools_succeeded": episode_data.get("tools_succeeded", []),
            "tools_failed": episode_data.get("tools_failed", []),
            "fallbacks_triggered": episode_data.get("fallbacks_triggered", []),
            "strategy": episode_data.get("strategy", "default"),
            "strategy_effectiveness": episode_data.get("strategy_effectiveness", 0.0),
            "synthesis_conflicts_found": episode_data.get("synthesis_conflicts_found", 0),
            "synthesis_conflicts_resolved": episode_data.get("synthesis_conflicts_resolved", 0),
            "total_duration_seconds": episode_data.get("total_duration_seconds", 0.0),
            "error_patterns": episode_data.get("error_patterns", []),
            "lessons": episode_data.get("lessons", []),
            "metrics": episode_data.get("metrics", {})
        }
        self.episodes.append(episode)
        self._save()
        return episode
    
    def get_relevant_episodes(self, query_type: str, limit: int = 5) -> List[Dict]:
        """Retrieve past episodes matching a query type."""
        matches = [ep for ep in self.episodes if ep.get("query_type") == query_type]
        matches.sort(key=lambda x: x.get("strategy_effectiveness", 0), reverse=True)
        return matches[:limit]
    
    def get_tool_reliability(self, tool_name: str) -> Dict:
        """Calculate success rate for a specific tool across all episodes."""
        total = 0
        succeeded = 0
        failed = 0
        for ep in self.episodes:
            if tool_name in ep.get("tools_used", []):
                total += 1
                if tool_name in ep.get("tools_succeeded", []):
                    succeeded += 1
                if tool_name in ep.get("tools_failed", []):
                    failed += 1
        return {
            "tool": tool_name,
            "total_uses": total,
            "successes": succeeded,
            "failures": failed,
            "reliability": succeeded / total if total > 0 else 0.0
        }
    
    def get_best_strategy(self, query_type: str) -> Optional[Dict]:
        """Find the highest-performing strategy for a query type."""
        relevant = self.get_relevant_episodes(query_type)
        if not relevant:
            return None
        best = relevant[0]  # Already sorted by effectiveness
        return {
            "strategy": best.get("strategy"),
            "effectiveness": best.get("strategy_effectiveness"),
            "tools_used": best.get("tools_used"),
            "from_episode": best.get("episode_id")
        }
    
    def get_error_patterns(self) -> Dict[str, int]:
        """Aggregate error patterns across all episodes."""
        patterns = {}
        for ep in self.episodes:
            for pattern in ep.get("error_patterns", []):
                patterns[pattern] = patterns.get(pattern, 0) + 1
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))
    
    def get_all_episodes(self) -> List[Dict]:
        """Return all episodes."""
        return self.episodes
    
    def get_summary(self) -> Dict:
        """Get a summary of episodic memory for the agent's context."""
        if not self.episodes:
            return {"total_episodes": 0, "message": "No prior research episodes recorded."}
        
        tool_stats = {}
        for ep in self.episodes:
            for tool in ep.get("tools_used", []):
                if tool not in tool_stats:
                    tool_stats[tool] = self.get_tool_reliability(tool)
        
        return {
            "total_episodes": len(self.episodes),
            "query_types_seen": list(set(ep.get("query_type", "unknown") for ep in self.episodes)),
            "avg_effectiveness": sum(ep.get("strategy_effectiveness", 0) for ep in self.episodes) / len(self.episodes),
            "tool_reliability": tool_stats,
            "common_errors": dict(list(self.get_error_patterns().items())[:5])
        }
