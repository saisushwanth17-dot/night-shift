"""Repository inspection tools exposed to the Strands Agent."""

from pathlib import Path
from strands import tool

from nightshift.policy.engine import PolicyEngine

policy_engine = PolicyEngine()


@tool
def repo_list_files(directory_path: str = ".") -> dict:
    """List source, test, and configuration files in the target repository.
    
    Args:
        directory_path: Relative directory path to inspect.
    """
    target = Path(directory_path)
    if not target.exists():
        return {"success": False, "error": f"Directory '{directory_path}' does not exist."}

    files = []
    for p in target.rglob("*"):
        if any(part.startswith(".") for part in p.parts if part != "."):
            continue
        if "__pycache__" in p.parts or "node_modules" in p.parts or ".venv" in p.parts:
            continue
        if p.is_file():
            files.append(p.as_posix())

    return {
        "success": True,
        "total_files": len(files),
        "files": files[:50],
    }


@tool
def repo_read_file(file_path: str) -> dict:
    """Read the contents of a file in the repository.
    
    Args:
        file_path: Relative path to the file.
    """
    target = Path(file_path)
    if not target.exists():
        return {"success": False, "error": f"File '{file_path}' does not exist."}

    if target.stat().st_size > 100_000:
        return {"success": False, "error": f"File '{file_path}' exceeds maximum read size limit."}

    try:
        content = target.read_text(encoding="utf-8")
        return {"success": True, "file_path": file_path, "content": content}
    except Exception as ex:
        return {"success": False, "error": str(ex)}


@tool
def repo_search_text(query: str, directory_path: str = ".") -> dict:
    """Search for a text string or pattern across repository source files.
    
    Args:
        query: String to search for.
        directory_path: Relative path of directory to search within.
    """
    target = Path(directory_path)
    matches = []

    for p in target.rglob("*"):
        if any(part.startswith(".") for part in p.parts if part != "."):
            continue
        if "__pycache__" in p.parts or "node_modules" in p.parts or ".venv" in p.parts:
            continue
        if p.is_file() and p.suffix in [".py", ".ts", ".js", ".json", ".md", ".txt", ".toml", ".yaml", ".yml"]:
            try:
                lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
                for idx, line in enumerate(lines, start=1):
                    if query.lower() in line.lower():
                        matches.append({
                            "file": p.as_posix(),
                            "line_number": idx,
                            "content": line.strip(),
                        })
                        if len(matches) >= 30:
                            break
            except Exception:
                continue

    return {
        "success": True,
        "query": query,
        "total_matches": len(matches),
        "matches": matches,
    }
