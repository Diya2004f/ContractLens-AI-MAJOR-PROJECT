import os
import streamlit as st
st.set_page_config(
    page_title="ContractLens AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

#THEME
if "dark" not in st.session_state:
    st.session_state.dark = True
toggle = st.checkbox("🌙 Dark Mode", value=st.session_state.dark)
st.session_state.dark = toggle
theme_class = "dark" if st.session_state.dark else "light"
st.markdown(f"<body class='{theme_class}'>", unsafe_allow_html=True)

#  CSS
with open("styles.css", "r", encoding="utf-8") as f:
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

# HEADER
st.markdown("<h1 class='title-center'>ContractLens AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-center'>Understand contracts and legal documents instantly.</p>", unsafe_allow_html=True)

# UPLOAD
uploaded = st.file_uploader("", type=["pdf", "docx", "txt"], label_visibility="collapsed")
st.markdown("<p class='upload-help'>Supports PDF, DOCX, TXT (max 10 MB)</p>", unsafe_allow_html=True)

if uploaded:
    if uploaded.size > 10 * 1024 * 1024:
        st.error("❌ File too large. Please upload ≤ 10 MB.")
    else:
        st.success("✅ File uploaded successfully!")
        st.session_state["uploaded_file"] = uploaded

        if st.button("Summarize Document", use_container_width=True):
            st.switch_page("pages/Summary.py")

# FOOTER
st.markdown("""
<div class="footer">
Your document remains private and is never stored.<br>
AI for Legal Clarity
</div>
""", unsafe_allow_html=True)
