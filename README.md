# Quality Gates (Bullets • Cover Letter • Skills Gaps)

## 1) Tailored Bullets — Must Pass All
- [ ] **Count:** 3–6 bullets total.
- [ ] **Length:** Each bullet ≤ 2 lines (wrap width ~80–100 chars).
- [ ] **Verbs:** Each begins with a strong action verb (Built, Led, Quantified, Shipped…).
- [ ] **Mapping:** Each bullet ends with a brief parenthetical mapping to a posting must-have.  
      _Example:_ “(maps to: ‘build and evaluate ML models’)”
- [ ] **Numbers:** ≥2 bullets include concrete numbers (scope, scale, impact, time).
- [ ] **Truth:** No claims that aren’t in `data/resume.md`.

**Red flags to reject**
- Generic phrasing (“team player,” “fast learner”).
- Vague impact (“improved,” “helped”) with no measurable context.
- Bullets that don’t clearly map to any posting requirement.

---

## 2) Cover Letter — Must Pass All
- [ ] **Length:** ~300–350 words after post-processing.
- [ ] **Structure:** Clear opening (why this company/role) → 2–3 concrete matches → confident close (CTA).
- [ ] **Specificity:** Includes at least **2 resume-backed** examples tied to posting must-haves.
- [ ] **Tone:** Confident, specific, not boastful; US English; no clichés.
- [ ] **Truth:** No new claims beyond `resume.md`.

**Red flags to reject**
- Company boilerplate (could apply to anyone).
- Skills listed that aren’t in resume.
- Wall of text (no paragraphing) or >350 words after trimming.

---

## 3) Skills Gaps — Must Pass All
- [ ] **Count:** 2–5 gaps max.
- [ ] **Actionability:** Each gap has 1–2 **practical**, near-term steps (course + small deliverable).
- [ ] **Relevance:** Gaps reflect actual posting must-haves missing from the resume.
- [ ] **Brevity:** One line per step; concrete nouns/verbs, no fluff.

**Good step template**
- “Complete ___ (6–8 hrs); ship a ___ replicating posting KPI ___.”
- “Implement a small ___ in GitHub (readme + screenshot) by ___ date.”

---

## 4) Quick Rubric (0–2 each; pass = ≥8/10)
- **Relevance to Must-Haves:** 0 (off) 1 (partial) 2 (tight mapping)
- **Specificity/Numbers:** 0 (none) 1 (some) 2 (clear, ≥2 quantified)
- **Brevity/Clarity:** 0 (rambling) 1 (ok) 2 (crisp ≤2 lines/bullet, ~325w letter)
- **Truthfulness:** 0 (fabrication) 1 (borderline) 2 (strictly resume-backed)
- **Actionability of Gaps:** 0 (hand-wavy) 1 (some) 2 (clear steps & deliverables)

---

## 5) Reviewer Script (60–90s manual check)
1. **Scan bullets** top-down: count (3–6), verbs, ≤2 lines, ≥2 numbers.
2. **Check parentheses:** each bullet has “(maps to: …)” and matches a Must-Have from the posting file.
3. **Truth sweep:** anything not in `resume.md`? If yes → move to Skills Gap or delete.
4. **Cover letter word count:** ~300–350 after trim; opening/middle/close present.
5. **Gaps:** 2–5 items; each with 1–2 concrete steps producing a small artifact (repo, dashboard, notebook).

---

## 6) Examples

**Bullet (good)**
- Built LightGBM model on 2M+ SPARCS rows; segmented by LOS/diagnosis to cut MAE to ~\$10.5K; documented SHAP drivers for cost insight **(maps to: “build & evaluate ML models; interpretability”)**

**Gap + Steps (good)**
- **Production ML (missing):**  
  - Finish “Intro to MLflow” (4–6 hrs); log an experiment and write a 1-page readme.  
  - Containerize a toy model (FastAPI) and deploy locally; include a cURL example.

---

## 7) Automation Notes (for later code)
- Post-processor trims cover-letter to 350 words and rejects bullets >2 lines.
- Prompts require mapping parentheticals; you can strip them before submission.
- `run_metadata.json` stores token counts to watch costs per run.