"""SQLite-backed Engineering Memory Store for Night Shift."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from nightshift.config import settings
from nightshift.memory.models import IncidentRecord, MaintenanceSession, RepoProfile


class EngineeringMemoryStore:
    """Stores repository conventions, past incident remediations, and operational sessions."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database tables for memory persistence."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Repo profiles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repo_profiles (
                    repo_name TEXT PRIMARY KEY,
                    language TEXT NOT NULL,
                    package_manager TEXT NOT NULL,
                    test_command TEXT NOT NULL,
                    lint_command TEXT NOT NULL,
                    default_branch TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # 2. Incident remediation memory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    repo_name TEXT NOT NULL,
                    failure_signature TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    suspect_file TEXT NOT NULL,
                    patch_diff TEXT NOT NULL,
                    attempts_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    pr_url TEXT,
                    pr_branch TEXT,
                    duration_ms REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            # 3. Operational sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    repo_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    incidents_handled INTEGER NOT NULL DEFAULT 0,
                    prs_opened INTEGER NOT NULL DEFAULT 0,
                    blocked_count INTEGER NOT NULL DEFAULT 0,
                    duration_minutes REAL NOT NULL DEFAULT 0.0
                )
            """)
            conn.commit()

    def save_repo_profile(self, profile: RepoProfile) -> None:
        """Persist or update repository conventions profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO repo_profiles
                (repo_name, language, package_manager, test_command, lint_command, default_branch, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.repo_name,
                profile.language,
                profile.package_manager,
                profile.test_command,
                profile.lint_command,
                profile.default_branch,
                profile.updated_at.isoformat(),
            ))
            conn.commit()

    def get_repo_profile(self, repo_name: str) -> RepoProfile | None:
        """Retrieve repository profile if previously stored."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repo_profiles WHERE repo_name = ?", (repo_name,))
            row = cursor.fetchone()
            if not row:
                return None
            return RepoProfile(
                repo_name=row["repo_name"],
                language=row["language"],
                package_manager=row["package_manager"],
                test_command=row["test_command"],
                lint_command=row["lint_command"],
                default_branch=row["default_branch"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def record_incident(self, incident: IncidentRecord) -> None:
        """Store an incident remediation event in engineering memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO incidents
                (incident_id, repo_name, failure_signature, hypothesis, suspect_file,
                 patch_diff, attempts_count, status, pr_url, pr_branch, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident.incident_id,
                incident.repo_name,
                incident.failure_signature,
                incident.hypothesis,
                incident.suspect_file,
                incident.patch_diff,
                incident.attempts_count,
                incident.status,
                incident.pr_url,
                incident.pr_branch,
                incident.duration_ms,
                incident.created_at.isoformat(),
            ))
            conn.commit()

    def find_similar_remediation(self, failure_signature: str, repo_name: str | None = None) -> list[IncidentRecord]:
        """Query memory for previously successful remediations with similar failure signatures."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Substring match on failure signature
            query = "SELECT * FROM incidents WHERE status = 'RESOLVED' AND failure_signature LIKE ?"
            params = [f"%{failure_signature}%"]
            if repo_name:
                query += " AND repo_name = ?"
                params.append(repo_name)
            query += " ORDER BY created_at DESC LIMIT 5"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                IncidentRecord(
                    incident_id=r["incident_id"],
                    repo_name=r["repo_name"],
                    failure_signature=r["failure_signature"],
                    hypothesis=r["hypothesis"],
                    suspect_file=r["suspect_file"],
                    patch_diff=r["patch_diff"],
                    attempts_count=r["attempts_count"],
                    status=r["status"],
                    pr_url=r["pr_url"],
                    pr_branch=r["pr_branch"],
                    duration_ms=r["duration_ms"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]

    def get_recent_incidents(self, repo_name: str | None = None, limit: int = 10) -> list[IncidentRecord]:
        """Fetch recent incident records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if repo_name:
                cursor.execute(
                    "SELECT * FROM incidents WHERE repo_name = ? ORDER BY created_at DESC LIMIT ?",
                    (repo_name, limit),
                )
            else:
                cursor.execute("SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [
                IncidentRecord(
                    incident_id=r["incident_id"],
                    repo_name=r["repo_name"],
                    failure_signature=r["failure_signature"],
                    hypothesis=r["hypothesis"],
                    suspect_file=r["suspect_file"],
                    patch_diff=r["patch_diff"],
                    attempts_count=r["attempts_count"],
                    status=r["status"],
                    pr_url=r["pr_url"],
                    pr_branch=r["pr_branch"],
                    duration_ms=r["duration_ms"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]

    def start_session(self, repo_name: str) -> MaintenanceSession:
        """Start a new maintenance shift session."""
        session_id = f"shift-{uuid.uuid4().hex[:8]}"
        session = MaintenanceSession(session_id=session_id, repo_name=repo_name)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, repo_name, start_time)
                VALUES (?, ?, ?)
            """, (session.session_id, session.repo_name, session.start_time.isoformat()))
            conn.commit()
        return session

    def close_session(
        self,
        session_id: str,
        incidents_handled: int,
        prs_opened: int,
        blocked_count: int,
    ) -> MaintenanceSession:
        """Close a maintenance shift session and calculate total duration."""
        end_time = datetime.now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_time, repo_name FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Session '{session_id}' not found.")

            start_time = datetime.fromisoformat(row["start_time"])
            duration_minutes = (end_time - start_time).total_seconds() / 60.0

            cursor.execute("""
                UPDATE sessions
                SET end_time = ?, incidents_handled = ?, prs_opened = ?, blocked_count = ?, duration_minutes = ?
                WHERE session_id = ?
            """, (
                end_time.isoformat(),
                incidents_handled,
                prs_opened,
                blocked_count,
                round(duration_minutes, 2),
                session_id,
            ))
            conn.commit()

            return MaintenanceSession(
                session_id=session_id,
                repo_name=row["repo_name"],
                start_time=start_time,
                end_time=end_time,
                incidents_handled=incidents_handled,
                prs_opened=prs_opened,
                blocked_count=blocked_count,
                duration_minutes=round(duration_minutes, 2),
            )
