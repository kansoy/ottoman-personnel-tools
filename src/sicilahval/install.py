"""Install a self-contained skill for local agents or ZIP-based clients."""
from __future__ import annotations

import shutil
from pathlib import Path

def install_skill(target: str = "codex", scope: str = "project", path: str | Path | None = None) -> dict:
    if target not in ("codex", "claude", "agents") or scope not in ("project", "user"):
        raise ValueError("Unsupported skill target/scope")
    base = Path(path).expanduser() if path is not None else (
        Path.home() if scope == "user" else Path.cwd()) / {
            "codex": ".codex/skills", "claude": ".claude/skills", "agents": ".agents/skills"}[target]
    resource = Path(__file__).with_name("skill")
    if not (resource / "SKILL.md").is_file():
        raise ValueError("Bundled skill instructions are missing from this installation")
    destination = base / "sicilahval"
    if destination.exists():
        raise ValueError(f"Skill already exists; preserve/review it before replacing: {destination}")
    base.mkdir(parents=True, exist_ok=True)
    shutil.copytree(resource, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    scripts = destination / "scripts"
    scripts.mkdir(exist_ok=True)
    vendor = scripts / "_sicilahval"
    package_root = Path(__file__).parent
    shutil.copytree(package_root, vendor, ignore=shutil.ignore_patterns("skill", "__pycache__", "*.pyc"))
    (scripts / "sicilahval.py").write_text(
        '"""Offline skill entry point; no installed package or API key required."""\n'
        "from _sicilahval.cli import main\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n", encoding="utf-8")
    return {"skill": "sicilahval", "path": str(destination), "target": target, "scope": scope,
            "offline_command": f"python {destination / 'scripts/sicilahval.py'} --help",
            "pdf_dependency": "pypdf is optional; TXT/MD/DOCX use Python standard library"}
