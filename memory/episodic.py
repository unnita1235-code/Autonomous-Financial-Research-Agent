import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EpisodicMemory:
    """
    Layer 3 Memory: Stores high-level research episodes, strategies, 
    and lessons learned to improve future agent performance.
    """
    def __init__(self, storage_path: str = "database/episodic_memory.json"):
        self.storage_path = storage_path
        self.episodes: List[Dict[str, Any]] = []
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.episodes = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load episodic memory: {e}")
                self.episodes = []
        else:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            self.episodes = []

    def save_episode(self, query: str, strategy: List[str], outcome: str, lessons: Optional[str] = None):
        """
        Saves a research episode.
        """
        episode = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "tools_used": strategy,
            "outcome_summary": outcome[:200] + "..." if len(outcome) > 200 else outcome,
            "lessons_learned": lessons or "Standard research path successful."
        }
        self.episodes.append(episode)
        self._persist()

    def _persist(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.episodes[-100:], f, indent=2) # Keep last 100 episodes
        except Exception as e:
            logger.error(f"Failed to persist episodic memory: {e}")

    def get_relevant_lessons(self, query: str) -> str:
        """
        Simple heuristic retrieval of lessons learned from past similar queries.
        In a production system, this would use the vector store.
        """
        # For now, return the most recent 3 lessons as context
        if not self.episodes:
            return "No previous episodic context available."
        
        recent = self.episodes[-3:]
        context = "Recent Research Lessons:\n"
        for ep in recent:
            context += f"- Task: {ep['query']} | Lesson: {ep['lessons_learned']}\n"
        return context
