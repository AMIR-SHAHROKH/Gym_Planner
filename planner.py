import os
from dotenv import load_dotenv
import streamlit as st
import openai

# Load environment variables from .env file
load_dotenv()

# ───── CSS for style tweaks ─────
st.markdown(
    """
    <style>
    [aria-label="Copy code"] {
        transform: scale(1.5);
        transform-origin: top right;
        transition: none !important;
    }
    [aria-label="Copy code"]:active {
        animation: none !important;
    }
    div[data-testid="stCodeBlock"] > pre {
        padding-top: 2.5rem !important;
    }
    div[data-testid="stCodeBlock"] {
        padding-bottom: 1.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ───── Remove proxy envs ─────
for var in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(var, None)

# ───── OpenAI API Key ─────
openai.api_key = os.getenv("OPENAI_API_KEY", None) or st.secrets.get("OPENAI_API_KEY")
if not openai.api_key:
    st.error("❌ OpenAI API key not found. Add it to your .env file.")
    st.stop()
print(openai.api_key)
# ───── Questions ─────
QUESTIONS = [
    {"key": "name", "label": "What’s your name?", "type": "text"},
    {"key": "age", "label": "Age", "type": "number", "min": 10, "max": 100,  "default": 25},
    {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"]},
    {"key": "height", "label": "Height (cm)", "type": "number", "min": 100, "max": 250, "default": 185},
    {"key": "weight", "label": "Weight (kg)", "type": "number", "min": 30, "max": 200, "default": 80},
    {"key": "activity_level", "label": "Activity Level", "type": "select", "options": [
        "Sedentary (little to no exercise)",
        "Lightly Active (1–3 days/week)",
        "Moderately Active (3–5 days/week)",
        "Very Active (6–7 days/week)",
    ]},
    {"key": "goal", "label": "Your main goal", "type": "select", "options": ["Lose Weight", "Build Muscle", "Maintain Weight"]},
    {"key": "diet", "label": "Dietary preferences/restrictions", "type": "multiselect", "options": [
        "No Restrictions", "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "No Pork", "No Beef",
    ]},
    {"key": "workout_days", "label": "Workout days per week", "type": "number", "min": 1, "max": 7},
]

# ───── Init session state ─────
if 'plan' not in st.session_state:
    st.session_state.plan = None
if 'farsi_plan' not in st.session_state:
    st.session_state.farsi_plan = None

# ───── UI ─────
st.title("🏋️ Gym & 🍎 Meal Planner Bot")
st.markdown("Fill out the form below and I’ll generate a 30-day gym and meal plan just for you!")

with st.form("planner_form"):
    for q in QUESTIONS:
        if q["type"] == "text":
            st.text_input(q["label"], key=q["key"], value=q.get("default", ""))
        elif q["type"] == "number":
            st.number_input(
                q["label"],
                min_value=q["min"],
                max_value=q["max"],
                key=q["key"],
                value=q.get("default", q["min"])
            )
        elif q["type"] == "select":
            st.selectbox(q["label"], q["options"], key=q["key"])
        elif q["type"] == "multiselect":
            st.multiselect(q["label"], q["options"], key=q["key"])
    submitted = st.form_submit_button("Generate My 30-Day Plan")

    if submitted:
        name = st.session_state.name
        gender = st.session_state.gender

        details = "\n".join([
            f"- {q['label']}: {st.session_state[q['key']]}" for q in QUESTIONS if q['key'] != "name"
        ])

        prompt = (
            f"You're a personal trainer and nutritionist talking to a client named {name}, who identifies as {gender.lower()}.\n"
            "Use a warm, friendly tone—not robotic or generic AI style.\n"
            "Based on the following info, write a full 30-day gym + meal plan:\n\n"
            f"{details}\n\n"
            "Speak directly to them (like: 'Hey Amir! Here's what I suggest...').\n"
            "Include:\n"
            "- Daily gym plan (exercises, sets, reps, rest)\n"
            "- Daily meal plan (breakfast, lunch, dinner, snacks)\n"
            "- Daily total macros (calories, protein, carbs, fat)\n"
        )

        with st.spinner("💡 Crafting your personalized 30-day plan..."):
            res = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a friendly, motivational fitness coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.75,
                max_tokens=2500,
            )
            st.session_state.plan = res.choices[0].message.content
            st.session_state.farsi_plan = None

# ───── Show Result ─────
if st.session_state.plan:
    st.markdown(f"### 📝 Hey {st.session_state.name}, here’s your 30‑day plan!")

    # Two-line gap for better readability
    st.markdown("\n\n")

    with st.expander("📋 Copy English plan"):
        st.code(st.session_state.plan, language="markdown")

    st.markdown("\n\n")  # extra spacing before full text
    st.markdown(st.session_state.plan)

    if st.button("📘 نمایش برنامه به فارسی"):
        if not st.session_state.farsi_plan:
            with st.spinner("در حال ترجمه..."):
                tr = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Translate to natural Persian (Farsi)."},
                        {"role": "user", "content": f"Please translate the following fitness plan to Farsi:\n\n{st.session_state.plan}"}
                    ],
                    temperature=0.3,
                    max_tokens=2500,
                )
                st.session_state.farsi_plan = tr.choices[0].message.content

    if st.session_state.farsi_plan:
        st.markdown("### 📝 برنامه ۳۰ روزه برای شما")

        with st.expander("📋 کپی برنامه فارسی"):
            st.code(st.session_state.farsi_plan, language="markdown")

        st.markdown(
            f"<div dir='rtl' style='text-align: right; font-family: Vazir, sans-serif;'>{st.session_state.farsi_plan}</div>",
            unsafe_allow_html=True
        )
