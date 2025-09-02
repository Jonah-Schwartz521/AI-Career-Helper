# streamlit_app.py
"""
Streamlit UI for AI-Career-Helper.

Features:
- Upload or select a resume and job posting.
- Generate tailored bullets, cover letter, and skills gaps.
- Preview outputs in tabs and download as a ZIP.
"""

import io
import os
import zipfile
import streamlit as st

from src.utils.io import read_file
from src.utils.prompts import load_prompts, fill_user_prompt, soft_trim
from src.utils.llm import run_llm
from src.utils.postprocess import postprocess_and_write


# --- Page setup ---
st.set_page_config(page_title="AI Career Helper", page_icon="🧰", layout="wide")
st.title("AI Career Helper 🧰")
st.caption("Tailor a posting + resume into bullets, cover letter, and skills gaps")


# --- Sidebar ---
model = st.sidebar.selectbox("Choose model", ["gpt-4o-mini", "gpt-4o"], index=0)


# --- Inputs ---
col1, col2 = st.columns(2, gap="large")
with col1:
    role = st.text_input("Role / Title", value="AI/ML Intern")
    company = st.text_input("Company", value="CCI")

with col2:
    st.markdown("**Resume source**")
    resume_file = st.file_uploader(
        "Upload your resume (.md or .txt)", type=["md", "txt"]
    )
    resume_path = st.text_input("Or path to repo resume", value="data/resume.md")

st.markdown("**Job posting**")
posting_src = st.radio(
    "Provide a job posting as:", ["Paste text", "Upload file", "Repo file"], horizontal=True
)

posting_text = ""
posting_path = ""

if posting_src == "Paste text":
    posting_text = st.text_area(
        "Paste trimmed posting",
        height=220,
        placeholder="MUST-HAVES...\nRESPONSIBILITIES...\nQUALIFICATIONS...",
    )
elif posting_src == "Upload file":
    up = st.file_uploader("Upload posting (.txt/.md)", type=["txt", "md"], key="posting_upload")
    if up:
        posting_text = up.read().decode("utf-8", errors="ignore")
else:
    posting_path = st.text_input("Path to repo posting", value="data/postings/2025-08-27_CCI_AI-ML-Intern.txt")
    if posting_path and os.path.exists(posting_path):
        posting_text = read_file(posting_path)


# --- Run button ---
run_btn = st.button("Generate application ✨", type="primary", use_container_width=True)


# --- Handler ---
if run_btn:
    try:
        # 1) Load prompts
        system_prompt, user_template = load_prompts(
            "prompts/system_job_tailor.md", "prompts/user_job_tailor.md"
        )

        # 2) Resolve resume text
        if resume_file is not None:
            resume_text = resume_file.read().decode("utf-8", errors="ignore")
        else:
            if not os.path.exists(resume_path):
                st.error(f"Resume not found: {resume_path}")
                st.stop()
            resume_text = read_file(resume_path)

        # 3) Resolve posting text
        if not posting_text.strip():
            st.error("Please provide a job posting (paste, upload, or repo path).")
            st.stop()

        posting_trimmed = soft_trim(posting_text, max_chars=4500)

        # 4) Fill prompt
        user_prompt = fill_user_prompt(
            template=user_template,
            role=role,
            company=company,
            posting=posting_trimmed,
            resume=resume_text,
        )

        # 5) Call model
        with st.spinner("Calling model..."):
            result = run_llm(system_prompt, user_prompt, model=model)

        model_output = result["text"]
        usage = result["usage"]
        model_name = result["model"]

        # 6) Write artifacts
        out_dir = postprocess_and_write(
            model_output,
            role=role,
            company=company,
            inputs={
                "system": system_prompt,
                "user": user_prompt,
                "resume": resume_text,
                "posting": posting_trimmed,
            },
            usage=usage,
            model_name=model_name,
        )

        # 7) Show results
        st.success(f"Artifacts written to: `{out_dir}`")

        b = read_file(os.path.join(out_dir, "bullets.md"))
        c = read_file(os.path.join(out_dir, "cover_letter.md"))
        g = read_file(os.path.join(out_dir, "skills_gaps.md"))

        t1, t2, t3 = st.tabs(["Bullets", "Cover Letter", "Skills Gaps"])
        with t1:
            st.markdown(b)
        with t2:
            st.markdown(c)
        with t3:
            st.markdown(g)

        # 8) Download zip
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            for fn in ["bullets.md", "cover_letter.md", "skills_gaps.md", "run_metadata.json"]:
                z.write(os.path.join(out_dir, fn), arcname=fn)
        mem.seek(0)
        st.download_button("Download ZIP", mem, file_name=f"{os.path.basename(out_dir)}.zip")

        # 9) Token usage
        st.caption(f"Model: **{model_name}** | Usage: {usage}")

    except Exception as e:
        st.error(f"Run failed: {e}")