import io, os, zipfile
from pathlib import Path
import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# --- Ensure project root is on sys.path so src.utils.* imports resolve reliably ---
import sys
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
print(f"[boot] sys.path[0]={sys.path[0]}")

# --- Boot diagnostics (print goes to terminal before Streamlit UI initializes) ---
print("[boot] starting streamlit_app.py (header)")

def _probe_openai_host(timeout_sec: float = 5.0) -> bool:
    try:
        with socket.create_connection(("api.openai.com", 443), timeout=timeout_sec):
            return True
    except Exception:
        return False

# Load .env explicitly from project root to avoid REPL/frame issues
try:
    env_path = Path(os.getcwd()) / ".env"
    loaded = load_dotenv(dotenv_path=env_path, override=True)
    print(f"[boot] .env load: path={env_path} loaded={loaded}")
except Exception as _e:
    print(f"[boot] .env load error: {_e.__class__.__name__}: {_e}")

# --- Page setup ---
st.set_page_config(page_title='AI Career Helper', page_icon="🧰", layout="wide")
st.title("AI Career Helper 🧰")
st.caption('Tailor a posting + resume into bullets, cover letter, and skill gaps')

# DEBUG marker so you know the script reached the frontend
st.write("🔧 App loaded; preparing UI…")

# --- Inputs ---
col1, col2 = st.columns(2, gap='large')
with col1:
    role = st.text_input('Role / Title', value='AI/ML Intern')
    company = st.text_input('Company', value='CCI')

with col2:
    st.markdown('**Resume source**')
    # ↓ allow PDF here
    resume_file = st.file_uploader(
        'Upload your resume (.md, .txt, or .pdf) *or* use repo file',
        type=['md', 'txt', 'pdf']
    )
    resume_path = st.text_input('Or path to resume file in repo', value='data/resume.md')

st.markdown('**Job posting**')
posting_src = st.radio('Provide a job posting as:', ['Paste text', 'Upload file', 'Repo file'], horizontal=True)

posting_text = ""
posting_path = ""

if posting_src == 'Paste text':
    posting_text = st.text_area("Paste trimmed posting", height=220, placeholder="MUST-HAVES...\nRESPONSIBILITIES...\nQUALIFICATIONS...")
elif posting_src == 'Upload file':
    up = st.file_uploader('Upload posting (.txt/.md)', type=['txt', 'md'], key='posting_upload')
    if up is not None:
        posting_text = up.read().decode('utf-8', errors='ignore')
else:
    posting_path = st.text_input('Path to posting in repo', value='data/postings/2025-08-27_CCI_AI-ML-Intern.txt')
    if posting_path and os.path.exists(posting_path):
        # Avoid importing project utils before the button; just read raw text here
        try:
            with open(posting_path, 'r', encoding='utf-8', errors='ignore') as f:
                posting_text = f.read()
        except Exception as _read_err:
            st.warning(f"Could not read posting file: {posting_path} — {_read_err}")

# Primary action button
run_btn = st.button("Generate application ✨", type="primary", use_container_width=True)

if run_btn:
    try:
        # Live progress UI
        with st.status("Starting run…", expanded=True) as status:
            st.write("Step 1/6 — Importing internal modules…")
            try:
                st.write("• importing src.utils.io …")
                from src.utils.io import read_file, ensure_dir
                st.write("  ↳ ok")

                st.write("• importing src.utils.prompts …")
                from src.utils.prompts import load_prompts, fill_user_prompt, soft_trim
                st.write("  ↳ ok")

                st.write("• importing src.utils.llm …")
                from src.utils.llm import run_llm
                st.write("  ↳ ok")

                st.write("• importing src.utils.postprocess …")
                from src.utils.postprocess import postprocess_and_write
                st.write("  ↳ ok")

                st.success("Internal modules imported ✔")
            except ModuleNotFoundError as imp_err:
                st.error("Python can't locate your project modules. Make sure the `src/` folder is in the same folder as this script and contains the expected files.")
                st.code(str(imp_err))
                st.info("I added a fix that injects the project root into `sys.path` at startup. If this still fails, check that `src/utils/*.py` exist.")
                status.update(label="Import failed", state="error")
                st.stop()
            except Exception as imp_err:
                st.error("Failed to import internal modules from src/*")
                st.exception(imp_err)
                status.update(label="Import failed", state="error")
                st.stop()

            st.write("Step 2/6 — Loading prompts…")
            try:
                system_prompt, user_template = load_prompts(
                    'prompts/system_job_tailor.md',
                    'prompts/user_job_tailor.md'
                )
                st.success("Prompts loaded ✔")
            except Exception as prompt_err:
                st.error("Could not load prompt files from prompts/.")
                st.exception(prompt_err)
                status.update(label="Prompt load failed", state="error")
                st.stop()

            st.write("Step 3/6 — Resolving resume source…")
            try:
                if resume_file is not None:
                    if resume_file.name.lower().endswith(".pdf"):
                        reader = PdfReader(resume_file)
                        pages = [p.extract_text() or "" for p in reader.pages]
                        resume_text = "\n".join(pages).strip()
                    else:
                        resume_text = resume_file.read().decode("utf-8", errors="ignore")
                else:
                    if not os.path.exists(resume_path):
                        st.error(f"Resume not found: {resume_path}")
                        status.update(label="Resume not found", state="error")
                        st.stop()
                    if resume_path.lower().endswith(".pdf"):
                        with open(resume_path, "rb") as f:
                            reader = PdfReader(f)
                            pages = [p.extract_text() or "" for p in reader.pages]
                            resume_text = "\n".join(pages).strip()
                    else:
                        resume_text = read_file(resume_path)
                if not resume_text.strip():
                    st.error("Resolved resume is empty.")
                    status.update(label="Empty resume", state="error")
                    st.stop()
                st.success("Resume resolved ✔")
            except Exception as resume_err:
                st.error("Failed while reading resume.")
                st.exception(resume_err)
                status.update(label="Resume read failed", state="error")
                st.stop()

            st.write("Step 4/6 — Validating job posting…")
            if not posting_text.strip():
                st.error('Please provide a job posting (paste, upload, or repo path).')
                status.update(label="Missing job posting", state="error")
                st.stop()
            posting_trimmed = soft_trim(posting_text, max_chars=12000)
            st.success("Posting captured ✔")

            st.write("Step 5/6 — Building prompts & calling model…")

            # Preflight checks before calling the model
            key = os.getenv("OPENAI_API_KEY", "").strip()
            if not key:
                st.error("OPENAI_API_KEY is missing. Add it to your .env and restart the app.")
                status.update(label="Missing OPENAI_API_KEY", state="error")
                st.stop()

            st.write("• probing network to api.openai.com …")
            if not _probe_openai_host():
                st.error("Cannot reach api.openai.com:443. Check Wi‑Fi/VPN/firewall and try again.")
                status.update(label="Network unreachable", state="error")
                st.stop()
            st.write("  ↳ ok")

            user_prompt = fill_user_prompt(
                template=user_template,
                role=role,
                company=company,
                resume=resume_text,
                posting=posting_trimmed,
            )
            try:
                with st.spinner('Calling model… (45s timeout)'):
                    def _call():
                        return run_llm(system_prompt, user_prompt, model='gpt-4o-mini')
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        fut = ex.submit(_call)
                        try:
                            result = fut.result(timeout=45)
                        except FuturesTimeoutError:
                            st.error("Model call timed out after 45s. Network may be slow or the API is stalling.")
                            status.update(label="Model call timed out", state="error")
                            st.stop()
                model_output = result['text']
                usage = result.get('usage', {})
                model_name = result.get('model', 'unknown')
                st.success("Model response received ✔")
            except Exception as llm_err:
                st.error("Model call failed. Check your API key and network.")
                st.exception(llm_err)
                status.update(label="Model call failed", state="error")
                st.stop()

            st.write("Step 6/6 — Writing artifacts to outputs/…")
            try:
                out_dir = postprocess_and_write(
                    model_output,
                    role=role,
                    company=company,
                    inputs={
                        'system': system_prompt,
                        'user': user_prompt,
                        'resume': resume_text,
                        'posting': posting_trimmed,
                    },
                    usage=usage,
                    model_name=model_name,
                )
            except Exception as write_err:
                st.error("Failed while writing artifacts to outputs/.")
                st.exception(write_err)
                status.update(label="Write failed", state="error")
                st.stop()

            # Finalize status before rendering results
            status.update(label=f"Done ✔ Artifacts in `{out_dir}`", state="complete")

        # Show results (after status block to keep it tidy)
        st.success(f'Artifacts written to: `{out_dir}`')
        b = read_file(os.path.join(out_dir, 'bullets.md'))
        c = read_file(os.path.join(out_dir, 'cover_letter.md'))
        g = read_file(os.path.join(out_dir, 'skills_gaps.md'))

        t1, t2, t3 = st.tabs(['Bullets', 'Cover Letter', 'Skills Gaps'])
        with t1: st.markdown(b)
        with t2: st.markdown(c)
        with t3: st.markdown(g)

        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as z:
            for fn in ['bullets.md', 'cover_letter.md', 'skills_gaps.md', 'run_metadata.json']:
                z.write(os.path.join(out_dir, fn), arcname=fn)
        mem.seek(0)
        st.download_button("Download ZIP", mem, file_name=f"{os.path.basename(out_dir)}.zip")

        st.caption(f"Model: **{model_name}** | Usage: {usage}")

    except Exception as e:
        st.error(f"Run failed: {e}")
        st.exception(e)