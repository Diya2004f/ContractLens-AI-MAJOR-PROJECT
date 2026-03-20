import re
import streamlit as st
from transformers import pipeline
import pdfplumber
import docx

st.set_page_config(page_title="Summary", layout="wide")

# CSS 
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<nav class="navbar">
  <a class="logo" href="/">ContractLens AI</a>
  <div class="nav-links">
    <a class="nav-item" href="/">Home</a>
    <a class="nav-item" href="/About">About</a>
  </div>
</nav>
""", unsafe_allow_html=True)

uploaded = st.session_state.get("uploaded_file")
if not uploaded:
    st.error("Please upload a document first.")
    st.stop()

# MODEL 
@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")
summarizer = load_summarizer()

# TEXT EXTRACTION
def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            texts = []
            for p in pdf.pages:
                page_text = p.extract_text()
                if page_text:
                    texts.append(page_text)
            return "\n".join(texts)

    if file.name.lower().endswith(".docx"):
        d = docx.Document(file)
        return "\n".join(p.text for p in d.paragraphs)

    return file.read().decode("utf-8", errors="ignore")

raw_text = extract_text(uploaded) or ""
text = re.sub(r"[ \t]+", " ", raw_text).strip()

# SUMMARY
def make_summary(src: str) -> str:
    chunk = src[:3500]
    try:
        out = summarizer(chunk, max_length=350, min_length=120, do_sample=False)[0]["summary_text"]
        return out.strip()
    except Exception:
        return "Unable to summarize this document."

if "summary_output" not in st.session_state:
    st.session_state.summary_output = make_summary(text)

# REPHRASE 
def rephrase(mode_desc: str):
    base = st.session_state.summary_output
    prompt = f"Rewrite the following in {mode_desc}:\n\n{base}"
    prompt = prompt[:3000]
    out = summarizer(prompt, max_length=300, min_length=80, do_sample=False)[0]["summary_text"]
    st.session_state.summary_output = out.strip()

# CLAUSES
CLAUSE_KEYWORDS = {
    "Payment Terms": ["payment", "fee", "invoice", "compensation", "payable", "deposit", "rent"],
    "Parties": ["party", "parties", "tenant", "landlord", "owner", "guest", "lessor", "lessee"],
    "Term / Duration": ["duration", "term", "period", "months", "effective", "expiry", "expire"],
    "Termination": ["terminate", "termination", "end", "notice", "breach", "cancel"],
    "Liability / Indemnity": ["liability", "indemnify", "indemnity", "damages", "claims"],
    "Governing Law / Venue": ["jurisdiction", "governing law", "venue", "court", "courts"],
    "Assignment": ["assign", "assignment", "transfer", "delegate"],
}

#RISK 
RISK_RULES = {
    "Payment Terms": {
        "high": ["penalty", "late fee", "interest", "non-refundable"],
        "medium": ["advance", "deposit", "installment"],
        "low": ["payment schedule", "invoice"]
    },
    "Termination": {
        "high": ["immediate termination", "without notice", "breach"],
        "medium": ["30 days notice", "written notice"],
        "low": ["mutual termination"]
    },
    "Liability / Indemnity": {
        "high": ["unlimited liability", "indemnify all", "hold harmless"],
        "medium": ["limited liability"],
        "low": ["reasonable efforts"]
    },
    "Governing Law / Venue": {
        "high": ["exclusive jurisdiction", "foreign court"],
        "medium": ["arbitration"],
        "low": ["local jurisdiction"]
    },
    "Assignment": {
        "high": ["cannot assign", "without consent"],
        "medium": ["with approval"],
        "low": ["freely assignable"]
    }
}

#RISK SCORING
def calculate_risk(snippet: str, clause: str):
    snippet = snippet.lower()

    rules = RISK_RULES.get(clause, {})

    for word in rules.get("high", []):
        if word in snippet:
            return "High"

    for word in rules.get("medium", []):
        if word in snippet:
            return "Medium"

    return "Low"

def split_paragraphs(txt: str):
    return [p.strip() for p in re.split(r"\n{2,}", txt) if p.strip()]

def split_sentences(paragraph: str):
    sents = re.split(r"(?<=[\.\?\!])\s+", paragraph.strip())
    return [s for s in sents if s]

from typing import List

def score_sentence(sentence: str, keywords: List[str]) -> int:
    score = 0
    for kw in keywords:
        score += len(re.findall(rf"\b{re.escape(kw)}\b", sentence, flags=re.IGNORECASE))
    return score

# CLAUSE EXTRACTION 
def best_clause_snippets(doc: str):
    results = {}
    paragraphs = split_paragraphs(doc)

    boilerplate = [
        r"PAYING-GUEST AGREEMENT.*?PARTIES",
        r"hereinafter.*?(referred|called).*?,?",
        r"Flat No\..*?,",
        r"Chhattisgarh.*?,",
        r"daughter of.*?,"
    ]

    for clause, keys in CLAUSE_KEYWORDS.items():
        scored = []
        for p in paragraphs:
            sents = split_sentences(p)
            for s in sents:
                sc = score_sentence(s, keys)
                if sc > 0:
                    scored.append((sc, s))

        if scored:
            best = sorted(scored, key=lambda x: x[0], reverse=True)[:2]
            clause_text = " ".join([b[1].strip() for b in best])

            for pattern in boilerplate:
                clause_text = re.sub(pattern, "", clause_text, flags=re.IGNORECASE)

            clause_text = re.sub(r"\s{2,}", " ", clause_text).strip()

            try:
                simplified = summarizer(
                    f"Simplify this legal clause:\n{clause_text}",
                    max_length=60,
                    min_length=15,
                    do_sample=False
                )[0]["summary_text"].strip()
            except:
                simplified = clause_text

            confidence = min(100, len(scored) * 10)
            risk = calculate_risk(simplified, clause)

            results[clause] = {
                "confidence": confidence,
                "snippet": simplified,
                "risk": risk
            }
    return results

detected_clauses = best_clause_snippets(text)

st.markdown("## 📌 Summary")

c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

with c1:
    if st.button("Plain English", use_container_width=True):
        rephrase("simple plain English")

with c2:
    if st.button("Professional", use_container_width=True):
        rephrase("professional business/legal English")

with c3:
    if st.button("Rephrase", use_container_width=True):
        rephrase("clear and concise style")

with c4:
    if st.button("Re-Summarize", use_container_width=True):
        st.session_state.summary_output = make_summary(text)

left, right = st.columns([2.2, 1.1], gap="large")

with left:
    st.text_area("", st.session_state.summary_output, height=300, key="summary_box")
    st.download_button(
        "Download Summary (TXT)",
        data=st.session_state.summary_output,
        file_name="summary.txt"
    )

with right:
    st.markdown("## 🧾 Detected Clauses")

    if detected_clauses:
        for clause, data in detected_clauses.items():
            snippet = data["snippet"]
            conf = data["confidence"]
            risk = data["risk"]

            risk_color = {
                "High": "#ff6b6b",
                "Medium": "#ffa500",
                "Low": "#6bd17a"
            }.get(risk, "#ffffff")

            with st.expander(f"{clause} • Risk: {risk} • confidence {conf}%"):
                st.markdown(
                    f"""
                    <div class="snippet-box">
                        <strong>{clause} – Extracted Clause:</strong><br><br>
                        {snippet}
                        <br><br>
                        <b style="color:{risk_color}">Risk Level: {risk}</b><br>
                        <b>Confidence:</b> {conf}%
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("No major clauses detected in this document.")
