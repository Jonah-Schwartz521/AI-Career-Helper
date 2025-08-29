from .io import read_file

PLACEHOLDERS = ("{{ROLE}}", "{{COMPANY}}", "{{POSTING}}", "{{RESUME}}")

def load_prompts(system_path: str, user_path: str) -> tuple[str, str]:
    """
    Load system and user prompt templates from disk.
    Returns (system_prompt, user_template).
    """
    system_prompt = read_file(system_path).strip()
    user_template = read_file(user_path).strip()
    return system_prompt, user_template

def fill_user_prompt(template: str, role: str, company: str, posting: str, resume: str) -> str:
    """
    Replace placeholders in the user prompt with actual values.
    """
    filled = (
        template
        .replace("{{ROLE}}", role)
        .replace("{{COMPANY}}", company)
        .replace("{{POSTING}}", posting.strip())
        .replace("{{RESUME}}", resume.strip())
    )

    # Check if any placeholder still remains 
    for ph in PLACEHOLDERS:
        if ph in filled:
            raise ValueError(f"Unreplaced placeholder left in template {ph}")
    return filled

def soft_trim(text: str, max_chars: int = 5000) -> str:
    """
    Trim overly long text to a safe character budget without breaking the run.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # try to cut at the last newline before the limit for a cleaner edge
    cut = text.rfind("\n", 0, max_chars)
    return text[: cut if cut != -1 else max_chars].rstrip() + "\n...[trimmed]..."