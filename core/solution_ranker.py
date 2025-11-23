from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import math
from datetime import datetime

from datetime import datetime
from core.models import RankedSolution

class SolutionRanker:
    def __init__(self):
        pass

    def _calculate_simplicity(self, solution: Dict[str, Any]) -> float:
        """
        Estimate simplicity based on number of steps and code changes.
        0.0 (complex) to 1.0 (simple).
        """
        steps = len(solution.get("steps", []))
        code_lines = sum(len(c.get("code", "").splitlines()) for c in solution.get("code_changes", []))
        
        # Heuristic: fewer steps and lines = simpler
        step_score = max(0, 1.0 - (steps * 0.1))
        code_score = max(0, 1.0 - (code_lines * 0.05))
        
        return (step_score + code_score) / 2

    def _calculate_recency_score(self, date_str: Optional[str]) -> float:
        """
        Calculate score based on recency.
        """
        if not date_str:
            return 0.5 # Neutral if unknown
        
        try:
            # Handle various date formats or assume YYYY-MM-DD
            # For this mock, let's assume we parse it or get a year
            # If date_str is just a year:
            if len(date_str) == 4 and date_str.isdigit():
                year = int(date_str)
                current_year = datetime.now().year
                age = current_year - year
                return max(0, 1.0 - (age * 0.1)) # -10% per year
            return 0.5
        except:
            return 0.5

    def _calculate_consensus(self, solution: Dict[str, Any], all_solutions: List[Dict[str, Any]]) -> float:
        """
        Estimate consensus by checking for similar keywords in other solutions.
        """
        keywords = set(solution.get("title", "").lower().split())
        matches = 0
        for other in all_solutions:
            if other == solution:
                continue
            other_keywords = set(other.get("title", "").lower().split())
            if len(keywords.intersection(other_keywords)) >= 2: # At least 2 common words
                matches += 1
        
        # Normalize: if 2 other agents agree, that's high consensus
        return min(1.0, matches * 0.5)

    def rank_solution(self, solution: Dict[str, Any], all_solutions: List[Dict[str, Any]]) -> float:
        """Calculate solution ranking score."""
        
        # Extract or default metrics
        confidence = solution.get("confidence", 0.5)
        simplicity = self._calculate_simplicity(solution)
        
        # Success rate (e.g. from SO votes, normalized 0-1)
        votes = solution.get("votes", 0)
        success_rate = min(1.0, math.log(votes + 1) / 10) if votes > 0 else 0.5
        
        recency = self._calculate_recency_score(solution.get("date"))
        consensus = self._calculate_consensus(solution, all_solutions)
        
        # Weighted sum
        score = (
            confidence * 0.3 +
            simplicity * 0.2 +
            success_rate * 0.3 +
            recency * 0.1 +
            consensus * 0.1
        )
        return score

    def _are_duplicates(self, sol1: Dict[str, Any], sol2: Dict[str, Any]) -> bool:
        """Check if two solutions are effectively the same."""
        # Simple Jaccard similarity on title words
        w1 = set(sol1.get("title", "").lower().split())
        w2 = set(sol2.get("title", "").lower().split())
        
        if not w1 or not w2:
            return False
            
        intersection = len(w1.intersection(w2))
        union = len(w1.union(w2))
        
        return (intersection / union) > 0.6 # 60% similarity threshold

    def _merge_solutions(self, solutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a list of duplicate solutions into one."""
        primary = solutions[0]
        
        # Boost confidence if multiple sources found it
        merged_confidence = min(1.0, primary.get("confidence", 0.5) + (len(solutions) - 1) * 0.1)
        
        # Collect all sources
        all_sources = []
        for s in solutions:
            all_sources.extend(s.get("sources", []))
            
        merged = primary.copy()
        merged["confidence"] = merged_confidence
        merged["sources"] = list(set(all_sources))
        
        return merged

    def rank_and_filter(self, raw_solutions: List[Dict[str, Any]]) -> List[RankedSolution]:
        """
        Main entry point to rank, deduplicate, and format solutions.
        """
        if not raw_solutions:
            return []

        # 1. Deduplicate
        unique_groups = []
        processed_indices = set()
        
        for i, sol in enumerate(raw_solutions):
            if i in processed_indices:
                continue
                
            group = [sol]
            processed_indices.add(i)
            
            for j, other in enumerate(raw_solutions):
                if j in processed_indices:
                    continue
                
                if self._are_duplicates(sol, other):
                    group.append(other)
                    processed_indices.add(j)
            
            unique_groups.append(group)
            
        merged_solutions = [self._merge_solutions(group) for group in unique_groups]
        
        # 2. Score
        scored_solutions = []
        for sol in merged_solutions:
            score = self.rank_solution(sol, merged_solutions)
            scored_solutions.append((score, sol))
            
        # 3. Sort
        scored_solutions.sort(key=lambda x: x[0], reverse=True)
        
        # 4. Format
        final_output = []
        for rank, (score, sol) in enumerate(scored_solutions, 1):
            # Generate explanation
            why = f"High confidence ({sol.get('confidence', 0):.2f})"
            if score > 0.8:
                why += " and strong consensus among agents."
            elif sol.get("votes", 0) > 50:
                why += " and community validated."
            else:
                why += "."
                
            # Trade-offs (placeholder logic)
            trade_offs = []
            if self._calculate_simplicity(sol) < 0.5:
                trade_offs.append("Complex implementation required.")
            else:
                trade_offs.append("Quick fix but may not address root cause.")

            final_output.append(RankedSolution(
                rank=rank,
                title=sol.get("title", "Untitled Solution"),
                description=sol.get("description", ""),
                steps=sol.get("steps", []),
                code_changes=sol.get("code_changes", []),
                confidence=sol.get("confidence", 0.0),
                sources=sol.get("sources", []),
                why_ranked_here=why,
                trade_offs=trade_offs
            ))
            
        return final_output
