"""Codebase Timeline Intelligence — Git history analysis.

Analyzes commit history to detect:
- Active vs abandoned modules
- High-change areas (bug-prone hotspots)
- Development velocity
- Contributor patterns
- Code age and evolution
"""
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class TimelineAnalyzer:
    """Analyzes git history for codebase evolution intelligence."""

    def analyze(self, repo_path: Path, max_commits: int = 500) -> dict:
        """Analyze git history. Returns timeline intelligence."""
        try:
            from git import Repo
            repo = Repo(str(repo_path))
        except Exception as e:
            logger.warning(f"Git history analysis failed: {e}")
            return {"error": str(e), "available": False}

        commits = list(repo.iter_commits(max_count=max_commits))
        if not commits:
            return {"error": "No commits found", "available": False}

        now = datetime.now(timezone.utc)

        # File change frequency
        file_changes: dict[str, list[dict]] = defaultdict(list)
        commit_data = []

        for commit in commits:
            ts = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
            age_days = (now - ts).days

            info = {
                "hash": commit.hexsha[:8],
                "message": commit.message.strip()[:120],
                "author": str(commit.author),
                "date": ts.isoformat(),
                "age_days": age_days,
            }
            commit_data.append(info)

            # Track changed files
            try:
                if commit.parents:
                    diffs = commit.diff(commit.parents[0])
                    for diff in diffs:
                        fp = diff.b_path or diff.a_path
                        if fp:
                            file_changes[fp].append({
                                "date": ts,
                                "age_days": age_days,
                                "author": str(commit.author),
                                "type": diff.change_type,
                            })
            except Exception:
                pass

        # Analysis
        result = {
            "available": True,
            "total_commits": len(commits),
            "time_span": self._time_span(commits),
            "active_modules": self._active_modules(file_changes, now),
            "abandoned_code": self._abandoned_code(file_changes, now),
            "hotspots": self._change_hotspots(file_changes),
            "velocity": self._velocity(commits, now),
            "contributors": self._contributors(commit_data),
            "recent_activity": commit_data[:10],
        }

        return result

    def _time_span(self, commits: list) -> dict:
        if not commits:
            return {}
        oldest = datetime.fromtimestamp(commits[-1].committed_date, tz=timezone.utc)
        newest = datetime.fromtimestamp(commits[0].committed_date, tz=timezone.utc)
        span = (newest - oldest).days
        return {
            "first_commit": oldest.isoformat(),
            "latest_commit": newest.isoformat(),
            "span_days": span,
            "span_human": f"{span // 365}y {(span % 365) // 30}m" if span > 365 else f"{span} days",
        }

    def _active_modules(self, file_changes: dict, now: datetime) -> list[dict]:
        """Find actively developed modules (changed in last 30 days)."""
        module_activity: dict[str, dict] = defaultdict(lambda: {"changes": 0, "recent": 0, "files": set()})

        for fp, changes in file_changes.items():
            parts = Path(fp).parts
            module = parts[0] if len(parts) > 1 else "root"
            module_activity[module]["files"].add(fp)
            for ch in changes:
                module_activity[module]["changes"] += 1
                if ch["age_days"] <= 30:
                    module_activity[module]["recent"] += 1

        active = []
        for mod, data in module_activity.items():
            if data["recent"] > 0:
                active.append({
                    "module": mod,
                    "total_changes": data["changes"],
                    "recent_changes": data["recent"],
                    "files": len(data["files"]),
                    "status": "active",
                })

        active.sort(key=lambda x: x["recent_changes"], reverse=True)
        return active[:15]

    def _abandoned_code(self, file_changes: dict, now: datetime) -> list[dict]:
        """Find files/modules not touched in 6+ months."""
        abandoned = []
        for fp, changes in file_changes.items():
            if not changes:
                continue
            latest = min(ch["age_days"] for ch in changes)
            if latest > 180:  # 6 months
                abandoned.append({
                    "file": fp,
                    "last_changed_days_ago": latest,
                    "total_changes": len(changes),
                    "status": "abandoned" if latest > 365 else "stale",
                })

        abandoned.sort(key=lambda x: x["last_changed_days_ago"], reverse=True)
        return abandoned[:20]

    def _change_hotspots(self, file_changes: dict) -> list[dict]:
        """Find files with the most changes (likely bug-prone)."""
        hotspots = []
        for fp, changes in file_changes.items():
            # Count unique authors
            authors = set(ch["author"] for ch in changes)
            hotspots.append({
                "file": fp,
                "total_changes": len(changes),
                "unique_authors": len(authors),
                "bug_risk": "high" if len(changes) > 20 else "medium" if len(changes) > 10 else "low",
            })

        hotspots.sort(key=lambda x: x["total_changes"], reverse=True)
        return hotspots[:15]

    def _velocity(self, commits: list, now: datetime) -> dict:
        """Calculate development velocity metrics."""
        if not commits:
            return {}

        # Commits per week (last 12 weeks)
        weekly = defaultdict(int)
        for c in commits:
            ts = datetime.fromtimestamp(c.committed_date, tz=timezone.utc)
            week = (now - ts).days // 7
            if week < 12:
                weekly[week] += 1

        weeks = list(range(12))
        commit_counts = [weekly.get(w, 0) for w in weeks]
        avg_per_week = sum(commit_counts) / max(1, len([c for c in commit_counts if c > 0]))

        # Trend: compare last 4 weeks to previous 4 weeks
        recent = sum(commit_counts[:4])
        older = sum(commit_counts[4:8])
        trend = "accelerating" if recent > older * 1.2 else "decelerating" if recent < older * 0.8 else "stable"

        return {
            "avg_commits_per_week": round(avg_per_week, 1),
            "last_4_weeks": recent,
            "previous_4_weeks": older,
            "trend": trend,
            "weekly_breakdown": commit_counts,
        }

    def _contributors(self, commit_data: list[dict]) -> dict:
        """Analyze contributor patterns."""
        author_counts = Counter(c["author"] for c in commit_data)
        total = len(commit_data)

        contributors = [
            {"name": name, "commits": count, "percentage": round(count / total * 100, 1)}
            for name, count in author_counts.most_common(10)
        ]

        # Bus factor (how many devs contribute 80% of commits)
        cumulative = 0
        bus_factor = 0
        for c in contributors:
            cumulative += c["percentage"]
            bus_factor += 1
            if cumulative >= 80:
                break

        return {
            "total": len(author_counts),
            "bus_factor": bus_factor,
            "top_contributors": contributors,
        }
