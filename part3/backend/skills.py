"""Skills: progressive disclosure of domain knowledge."""

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def skill_index() -> str:
    lines = []

    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        lines.append(
            f"- {path.parent.name}: {path.read_text(encoding='utf-8').splitlines()[1]}"
        )

    return "\n".join(lines)


def load_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"

    if not path.exists():
        return f"No skill named {name}. Available: {', '.join(available())}"

    return path.read_text(encoding="utf-8")


def available() -> list[str]:
    return sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
