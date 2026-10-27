"""Streamlit frontend for CodeMentor AI.

Start with: python -m streamlit run app.py
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
LANGUAGES = ("Python", "JavaScript", "Java", "C++", "Ruby", "Go")
LEVELS = ("Beginner", "Intermediate", "Advanced")

st.set_page_config(page_title="CodeMentor AI", page_icon="🧠", layout="wide")


def fetch_response(endpoint: str, payload: dict[str, str]) -> str | None:
    """Call the local API with explicit timeout and usable error messages."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/{endpoint}", json=payload, timeout=90
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get("response") if isinstance(result, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            st.error("The API returned an unexpected response format.")
            return None
        return answer
    except requests.exceptions.Timeout:
        st.error("The request timed out. Try again with a shorter input.")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend. Start FastAPI on the configured API URL.")
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        # Do not display raw provider exception data in the UI.
        message = "The API could not process your request."
        if exc.response is not None:
            try:
                detail = exc.response.json().get("detail")
                if isinstance(detail, str):
                    message = detail
                elif status == 422:
                    message = "Please check the required fields and input lengths."
            except (ValueError, AttributeError):
                pass
        st.error(f"{message} (HTTP {status})")
    except (requests.exceptions.RequestException, ValueError):
        st.error("Unable to read the API response. Check your backend logs.")
    return None


def show_result(key: str, filename: str) -> None:
    """Keep generated results visible across Streamlit reruns."""
    answer = st.session_state.get(key)
    if answer:
        st.divider()
        st.markdown(answer)
        st.download_button(
            "Download response",
            data=answer,
            file_name=filename,
            mime="text/markdown",
            key=f"download_{key}",
        )


st.title("🧠 CodeMentor AI")
st.caption("Understand concepts · Review your code · Learn from generated examples")
st.info(
    "An educational coding assistant. AI suggestions can be wrong: "
    "review code and test it in your own environment."
)

with st.sidebar:
    st.header("Learning settings")
    language = st.selectbox("Programming language", LANGUAGES)
    level = st.selectbox("Experience level", LEVELS)
    st.divider()
    st.caption("Backend address")
    st.code(API_BASE_URL, language=None)
    if st.button("Check backend connection"):
        try:
            ping = requests.get(f"{API_BASE_URL}/health", timeout=5)
            ping.raise_for_status()
            st.success("Local API is running (AI provider not checked).")
        except requests.exceptions.RequestException:
            st.error("The local API is not reachable.")

explain_tab, debug_tab, generate_tab = st.tabs(
    ["📖 Explain a concept", "🛠 Review / debug code", "💻 Generate an example"]
)

with explain_tab:
    st.subheader("Make a programming concept click")
    with st.form("explain_form"):
        topic = st.text_input(
            "What would you like to understand?",
            placeholder="e.g., Python decorators or JavaScript promises",
            max_chars=1000,
        )
        submitted_explain = st.form_submit_button("Explain concept", type="primary")
    if submitted_explain:
        if len(topic.strip()) < 2:
            st.warning("Enter a topic (at least 2 characters).")
        else:
            with st.spinner("Preparing explanation..."):
                answer = fetch_response(
                    "explain", {"language": language, "topic": topic, "level": level}
                )
            if answer is not None:
                st.session_state["explain_result"] = answer
    show_result("explain_result", "concept-explanation.md")

with debug_tab:
    st.subheader("Understand what may be going wrong")
    st.caption("Paste source code. Code is sent to the AI provider for analysis, not executed.")
    with st.form("debug_form"):
        code = st.text_area(
            "Code to review",
            height=220,
            placeholder="Paste your code here...",
            max_chars=15000,
        )
        context = st.text_input(
            "Error message or intended behavior (optional)",
            placeholder="e.g., IndexError when list is empty",
            max_chars=1000,
        )
        submitted_debug = st.form_submit_button("Review code", type="primary")
    if submitted_debug:
        if len(code.strip()) < 3:
            st.warning("Paste at least 3 characters of source code.")
        else:
            with st.spinner("Reviewing code..."):
                answer = fetch_response(
                    "debug", {"language": language, "code": code, "context": context}
                )
            if answer is not None:
                st.session_state["debug_result"] = answer
    show_result("debug_result", "code-review.md")

with generate_tab:
    st.subheader("Generate a small, educational example")
    with st.form("generate_form"):
        prompt = st.text_area(
            "Describe what you want to build",
            height=140,
            placeholder="e.g., A simple to-do list using Python classes",
            max_chars=1000,
        )
        submitted_generate = st.form_submit_button("Generate example", type="primary")
    if submitted_generate:
        if len(prompt.strip()) < 2:
            st.warning("Describe your example (at least 2 characters).")
        else:
            with st.spinner("Generating example..."):
                answer = fetch_response(
                    "generate", {"language": language, "topic": prompt, "level": level}
                )
            if answer is not None:
                st.session_state["generate_result"] = answer
    show_result("generate_result", "generated-example.md")

st.divider()
st.caption("Powered by Euri AI · FastAPI backend · Streamlit frontend")
