import json
import re
from datetime import datetime
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

STORE_DIR = Path("memory_store")
PROFILE_FILE = STORE_DIR / "user_profile.json"
HISTORY_FILE = STORE_DIR / "conversation_history.json"
MAX_RECENT = 50  # messages kept in rolling window


class JarvisMemory:
    def __init__(self):
        STORE_DIR.mkdir(exist_ok=True)
        (STORE_DIR / "chroma").mkdir(exist_ok=True)

        # ChromaDB — persistent semantic memory for past user messages
        self._chroma = chromadb.PersistentClient(path=str(STORE_DIR / "chroma"))
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = self._chroma.get_or_create_collection(
            name="jarvis_memory",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

        self._load_profile()
        self._load_history()

    # ------------------------------------------------------------------ profile

    def _load_profile(self):
        if PROFILE_FILE.exists():
            with open(PROFILE_FILE) as f:
                self.profile: dict = json.load(f)
        else:
            self.profile = {}

    def _save_profile(self):
        with open(PROFILE_FILE, "w") as f:
            json.dump(self.profile, f, indent=2)

    def set_fact(self, key: str, value: str):
        """Store or update a fact about the user (name, job, location, etc.)."""
        self.profile[key] = value
        self._save_profile()

    def profile_text(self) -> str:
        if not self.profile:
            return "No personal information stored yet."
        return "\n".join(f"- {k}: {v}" for k, v in self.profile.items())

    # ----------------------------------------------------------------- history

    def _load_history(self):
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE) as f:
                self._history: list[dict] = json.load(f)
        else:
            self._history = []

    def _save_history(self):
        self._history = self._history[-MAX_RECENT:]
        with open(HISTORY_FILE, "w") as f:
            json.dump(self._history, f, indent=2)

    def add_message(self, role: str, content: str):
        """Append a message to the rolling conversation history."""
        entry = {"role": role, "content": content, "ts": datetime.now().isoformat()}
        self._history.append(entry)
        self._save_history()

        # Index user messages semantically for future retrieval
        if role == "user":
            doc_id = f"u_{datetime.now().timestamp()}"
            self._collection.add(
                documents=[content],
                metadatas=[{"ts": entry["ts"]}],
                ids=[doc_id],
            )

    def recent_messages(self, n: int = 20) -> list[dict]:
        """Return the last n messages as {role, content} dicts."""
        return [{"role": m["role"], "content": m["content"]} for m in self._history[-n:]]

    # --------------------------------------------------------- semantic search

    def search(self, query: str, n: int = 4) -> list[str]:
        """Return the most semantically relevant past user messages."""
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(
            query_texts=[query],
            n_results=min(n, count),
        )
        return results["documents"][0] if results["documents"] else []


# --------------------------------------------------------- fact extraction util

_NAME_RE = re.compile(
    r"(?:my name is|i'm|i am|call me)\s+([A-Z][a-z]{1,20})", re.IGNORECASE
)
_JOB_RE = re.compile(
    r"(?:i(?:'m| am) (?:a |an )?|i work as (?:a |an )?)([a-z]+(?: [a-z]+){0,2})"
    r"(?= by profession| by trade| for work|[,.]|$)",
    re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    r"(?:i(?:'m| am) (?:from|in|based in)|i live in)\s+([A-Z][a-zA-Z ]{1,30})",
    re.IGNORECASE,
)
_SKIP_JOBS = {
    "not", "going", "trying", "looking", "wondering", "thinking", "asking",
    "here", "just", "really", "using", "building", "working",
}


def extract_facts(memory: JarvisMemory, text: str):
    """Parse obvious self-description facts from a user message and persist them."""
    m = _NAME_RE.search(text)
    if m:
        memory.set_fact("name", m.group(1).title())

    m = _JOB_RE.search(text)
    if m:
        job = m.group(1).strip().lower()
        if job not in _SKIP_JOBS:
            memory.set_fact("job", job)

    m = _LOCATION_RE.search(text)
    if m:
        memory.set_fact("location", m.group(1).strip())
