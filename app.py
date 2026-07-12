"""Fitness Assistant — a Streamlit app that builds personalized weekly plans
with Gemini and adapts them based on your weekly feedback.

Run with:  streamlit run app.py
"""

import json
import os
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai

# --- Configuration -----------------------------------------------------------

load_dotenv()

MODEL = "gemini-flash-latest"
DATA_DIR = Path(__file__).parent / "data"
PROFILE_PATH = DATA_DIR / "profile.json"
FEEDBACK_PATH = DATA_DIR / "feedback.json"


# --- Persistence helpers ------------------------------------------------------

def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return default
    return default


def _save(path: Path, value):
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(value, indent=2))


def load_profile():
    return _load(PROFILE_PATH, None)


def save_profile(profile):
    _save(PROFILE_PATH, profile)


def load_feedback():
    return _load(FEEDBACK_PATH, [])


def add_feedback(entry):
    history = load_feedback()
    history.append(entry)
    _save(FEEDBACK_PATH, history)
    return history


# --- Gemini -------------------------------------------------------------------

@st.cache_resource
def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY is not set. Add it to your .env file.")
        st.stop()
    return genai.Client(api_key=api_key)


def generate_plan(profile, feedback_history):
    client = get_client()

    recent = feedback_history[-3:]
    feedback_block = (
        "\n".join(
            f"- Week of {f['date']}: {f['text']}" for f in recent
        )
        or "No feedback yet — this is the first plan."
    )

    prompt = f"""You are an experienced personal trainer and nutrition coach.
Create a personalized 7-day fitness and nutrition plan for this client.

CLIENT PROFILE:
- Name: {profile['name']}
- Age: {profile['age']}
- Sex: {profile['sex']}
- Height: {profile['height_cm']} cm
- Weight: {profile['weight_kg']} kg
- Primary goal: {profile['goal']}
- Experience level: {profile['experience']}
- Days available per week: {profile['days_per_week']}
- Available equipment: {profile['equipment']}
- Injuries / limitations: {profile['limitations'] or 'None reported'}

RECENT WEEKLY FEEDBACK (adapt the new plan to address this):
{feedback_block}

Produce a clear, motivating plan in Markdown with:
1. A one-paragraph overview tailored to the goal and any feedback.
2. A day-by-day workout schedule (include rest days), with sets/reps or duration.
3. Simple daily nutrition guidance and an approximate calorie/protein target.
4. Two or three coaching tips for the week.
Keep it practical and safe. Respect any injuries or limitations."""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text


# --- Presentation helpers -----------------------------------------------------

def metric_cards(items):
    """items: list of (label, value, sub) tuples rendered as a row of cards."""
    cards = "".join(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-sub">{sub}</div>'
        f"</div>"
        for label, value, sub in items
    )
    st.markdown(f'<div class="metric-row">{cards}</div>', unsafe_allow_html=True)


def hero(title, subtitle):
    st.markdown(
        f'<div class="hero"><div class="hero-title">{title}</div>'
        f'<div class="hero-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


CSS = """
<style>
.block-container { max-width: 920px; padding-top: 2rem; }

/* Hero banner */
.hero {
    background: linear-gradient(120deg, #059669 0%, #22c55e 60%, #4ade80 100%);
    border-radius: 20px;
    padding: 2.2rem 2.4rem;
    margin-bottom: 1.6rem;
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.22);
}
.hero-title { font-size: 2.1rem; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
.hero-sub  { font-size: 1.02rem; color: rgba(255,255,255,0.92); margin-top: 0.35rem; }

/* Metric cards */
.metric-row { display: flex; flex-wrap: wrap; gap: 0.9rem; margin: 0.4rem 0 1.4rem; }
.metric-card {
    flex: 1 1 150px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}
.metric-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; }
.metric-value { font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-top: 0.15rem; line-height: 1.2; }
.metric-sub   { font-size: 0.8rem; color: #16a34a; margin-top: 0.15rem; }

/* Feedback timeline */
.fb-item {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #22c55e;
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.6rem;
}
.fb-date { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
.fb-text { font-size: 0.92rem; color: #334155; margin-top: 0.15rem; }

/* Primary button polish */
.stButton > button[kind="primary"] { border-radius: 10px; font-weight: 600; padding: 0.55rem 1.1rem; }

/* Section headings */
h3 { margin-top: 0.6rem; }
</style>
"""

GOALS = ["Lose fat", "Build muscle", "Improve endurance", "General fitness", "Strength"]
LEVELS = ["Beginner", "Intermediate", "Advanced"]


# --- UI -----------------------------------------------------------------------

st.set_page_config(page_title="Fitness Assistant", page_icon="💪", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

profile = load_profile()

# Two-step flow: profile setup -> plan. New users start on the profile page;
# returning users (profile already on file) land straight on the plan page.
if "step" not in st.session_state:
    st.session_state.step = "plan" if profile else "profile"


# ---- Step 1: Profile ---------------------------------------------------------
if st.session_state.step == "profile":
    hero(
        "Let's set up your profile" if not profile else "Edit your profile",
        "Tell us about yourself — your plan is built around this.",
    )

    with st.form("profile_form"):
        name = st.text_input("Name", value=(profile or {}).get("name", ""))
        col1, col2 = st.columns(2)
        age = col1.number_input("Age", 12, 100, value=(profile or {}).get("age", 30))
        sex = col2.selectbox(
            "Sex", ["Male", "Female", "Other"],
            index=["Male", "Female", "Other"].index((profile or {}).get("sex", "Male")),
        )
        height_cm = col1.number_input(
            "Height (cm)", 100, 250, value=(profile or {}).get("height_cm", 170)
        )
        weight_kg = col2.number_input(
            "Weight (kg)", 30, 300, value=(profile or {}).get("weight_kg", 70)
        )
        goal = st.selectbox(
            "Primary goal", GOALS,
            index=GOALS.index((profile or {}).get("goal", "General fitness")),
        )
        experience = st.select_slider(
            "Experience", LEVELS,
            value=(profile or {}).get("experience", "Beginner"),
        )
        days_per_week = st.slider(
            "Days available per week", 1, 7, value=(profile or {}).get("days_per_week", 3)
        )
        equipment = st.text_input(
            "Available equipment", value=(profile or {}).get("equipment", "Bodyweight only")
        )
        limitations = st.text_area(
            "Injuries / limitations", value=(profile or {}).get("limitations", "")
        )
        saved = st.form_submit_button(
            "Save & continue  →", type="primary", use_container_width=True
        )

    if saved:
        save_profile({
            "name": name, "age": age, "sex": sex,
            "height_cm": height_cm, "weight_kg": weight_kg,
            "goal": goal, "experience": experience,
            "days_per_week": days_per_week, "equipment": equipment,
            "limitations": limitations,
        })
        st.session_state.step = "plan"
        st.rerun()

    if profile:
        if st.button("← Back to plan", use_container_width=True):
            st.session_state.step = "plan"
            st.rerun()

    st.stop()


# ---- Step 2: Plan ------------------------------------------------------------
hero(
    f"Welcome, {profile['name']}" if profile.get("name") else "Your weekly plan",
    "Your adaptive weekly plan is ready to build.",
)

_, edit_col = st.columns([3, 1])
if edit_col.button("⚙️ Edit profile", use_container_width=True):
    st.session_state.step = "profile"
    st.rerun()

# Profile stats
metric_cards([
    ("Goal", profile["goal"], profile["experience"]),
    ("Training days", f"{profile['days_per_week']}/wk", profile["equipment"][:22]),
    ("Weight", f"{profile['weight_kg']} kg", f"{profile['height_cm']} cm tall"),
])

# Plan generation
left, right = st.columns([3, 1])
left.markdown("### 🗓️ This week's plan")
if right.button("✨ Generate", type="primary", use_container_width=True):
    with st.spinner("Building your personalized plan..."):
        st.session_state.plan = generate_plan(profile, load_feedback())

if st.session_state.get("plan"):
    with st.container(border=True):
        st.markdown(st.session_state.plan)
    st.download_button(
        "⬇️ Download plan (Markdown)",
        st.session_state.plan,
        file_name=f"fitness-plan-{date.today().isoformat()}.md",
        mime="text/markdown",
    )
else:
    st.info("Hit **✨ Generate** to create your personalized 7-day plan.")

st.divider()

# Feedback
st.markdown("### 📝 Weekly feedback")
st.caption("How did last week go? Your feedback shapes the next plan.")

fb_left, fb_right = st.columns([1, 1])

with fb_left:
    with st.form("feedback_form", clear_on_submit=True):
        feedback_text = st.text_area(
            "This week's notes",
            placeholder="e.g. Squats felt too easy, ran out of time on Thursday, knee felt sore...",
            label_visibility="collapsed",
            height=120,
        )
        submitted = st.form_submit_button("Submit feedback", type="primary", use_container_width=True)
        if submitted and feedback_text.strip():
            add_feedback({"date": date.today().isoformat(), "text": feedback_text.strip()})
            st.success("Saved — it'll shape your next plan.")

with fb_right:
    history = load_feedback()
    if history:
        st.markdown(f"**History** · {len(history)} ent"
                    f"{'ry' if len(history) == 1 else 'ries'}")
        for entry in reversed(history[-5:]):
            st.markdown(
                f'<div class="fb-item"><div class="fb-date">{entry["date"]}</div>'
                f'<div class="fb-text">{entry["text"]}</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No feedback yet. Your notes will appear here.")
