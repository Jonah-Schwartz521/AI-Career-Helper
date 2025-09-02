import os, re, json
from datetime import datetime
from typing import Tuple, Dict, Any
from src.utils.io import ensure_dir, sha256_text

SECTION_PATTERNS = {
    # Between "Tailored Bullets" and the next "## ..." header (typically Cover Letter)
    "bullets": re.compile(r"(?smi)^\s*##\s*Tailored Bullets\s*(.*?)(?=^\s*##\s+|$\Z)"),
    # Between "Cover Letter" and the next "## ..." header (typically Skills Gaps)
    "letter":  re.compile(r"(?smi)^\s*##\s*Cover Letter\s*(.*?)(?=^\s*##\s+|$\Z)"),
    # From "Skills Gaps (& Next Steps)" to end (or next header if you ever add more)
    "gaps":    re.compile(r"(?smi)^\s*##\s*Skills Gaps(?:\s*&\s*Next Steps)?\s*(.*?)(?=^\s*##\s+|$\Z)"),
}

def split_sections(model_output: str) -> Tuple[str, str, str]:
    """Return (bullets_md, cover_md, gaps_md). Empty strings if missing."""
    def grab(key):
        m = SECTION_PATTERNS[key].search(model_output)
        return (m.group(1).strip() if m else "")
    return grab("bullets"), grab("letter"), grab("gaps")

# --- quality gates ---

def enforce_bullets_rules(bullets_md: str) -> str:
    lines = [ln for ln in bullets_md.splitlines() if ln.strip().startswith("-")]
    lines = lines[:6]
    if len(lines) < 3:
        lines.append("- [Needs more bullets mapped to must-haves] (editor note)")
    lines = [ln.strip()[:240] for ln in lines]  # cap length
    return "\n".join(lines)

def enforce_letter_rules(letter_md: str, target_min=300, target_max=350) -> str:
    words = re.findall(r"\S+", letter_md)
    if len(words) > target_max:
        letter_md = " ".join(words[:target_max]) + " …"
    return letter_md.strip()

def enforce_gaps_rules(gaps_md: str) -> str:
    items = [ln for ln in gaps_md.splitlines() if ln.strip().startswith("-")]
    items = items[:5]
    if len(items) < 2:
        items.append("- [Add up to 2–5 skills gaps here] (editor note)")
    return "\n".join(items)

# --- writing artifacts ---

def output_folder(company: str, role: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d_%H%M%S")  # date + time
    slug = lambda s: re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return os.path.join("outputs", f"{slug(company)}_{slug(role)}_{date}")

def write_artifacts(out_dir: str, bullets: str, letter: str, gaps: str, metadata: Dict[str, Any]) -> None:
    ensure_dir(out_dir)
    with open(os.path.join(out_dir, "bullets.md"), "w", encoding="utf-8") as f:
        f.write("## Tailored Bullets\n" + bullets.strip() + "\n")
    with open(os.path.join(out_dir, "cover_letter.md"), "w", encoding="utf-8") as f:
        f.write("## Cover Letter\n" + letter.strip() + "\n")
    with open(os.path.join(out_dir, "skills_gaps.md"), "w", encoding="utf-8") as f:
        f.write("## Skills Gaps & Next Steps\n" + gaps.strip() + "\n")
    with open(os.path.join(out_dir, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def postprocess_and_write(model_output: str,
                          role: str,
                          company: str,
                          inputs: Dict[str, str],
                          usage: Dict[str, Any],
                          model_name: str) -> str:
    """Split, enforce gates, write artifacts. Returns output folder path."""
    bullets_md, letter_md, gaps_md = split_sections(model_output)
    bullets_md = enforce_bullets_rules(bullets_md)
    letter_md  = enforce_letter_rules(letter_md)
    gaps_md    = enforce_gaps_rules(gaps_md)

    out_dir = output_folder(company, role)
    metadata = {
        "role": role,
        "company": company,
        "model": model_name,
        "usage": usage,
        "inputs": {
            "system_hash":  sha256_text(inputs["system"]),
            "user_hash":    sha256_text(inputs["user"]),
            "resume_hash":  sha256_text(inputs["resume"]),
            "posting_hash": sha256_text(inputs["posting"]),
        },
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_artifacts(out_dir, bullets_md, letter_md, gaps_md, metadata)
    return out_dir