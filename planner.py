import os
from dotenv import load_dotenv
import streamlit as st
import openai
from fpdf import FPDF
import tempfile
import pyperclip
import requests

# ─── Load API key ───────────────────────────────────────────────────────────────
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not openai.api_key:
    st.error("❌ OpenAI API key not found.")
    st.stop()

# ─── Remove any proxy environment variables ──────────────────────────────────
for var in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(var, None)

# ─── Initialize session_state for plan and farsi_plan ───────────────────────────
if "plan" not in st.session_state:
    st.session_state.plan = None

if "farsi_plan" not in st.session_state:
    st.session_state.farsi_plan = None

# ─── Page UI & Styles ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Expert Gym & Meal Planner", layout="centered")
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #F5F3FF;
    color: #2E1A47;
}
h1, h2, h3 {
    color: #5E35B1;
}
button[kind="primary"] {
    background-color: #7E57C2 !important;
    color: white !important;
}
input, select, textarea {
    padding: 0.6rem;
    border-radius: 6px;
    border: 1px solid #D1C4E9;
    background-color: #FFFFFF; /* Changed to pure white */
    color: #4A148C;
}
input, textarea, select {
    background-color: #FFFFFF !important;  /* bright white */
    color: #000000 !important;  /* text color black for contrast */
}

/* Optional: remove input box shadows and borders to make it cleaner */
input:focus, textarea:focus, select:focus {
    outline: 2px solid #7E57C2 !important;  /* purple focus outline */
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)
st.title("🏋️ Personalized Gym & Meal Planner")
st.markdown("Fill out the form below — I’ll build you a **30‑day expert‑level plan**.")

# ─── Fields (Core + Additional) ────────────────────────────────────────────────
QUESTIONS = [
    {"key": "name", "label": "Name", "type": "text", "default": ""},
    {"key": "age", "label": "Age", "type": "number", "min": 10, "max": 100, "default": 25},
    {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"], "default": "Male"},
    {"key": "height", "label": "Height (cm)", "type": "number", "min": 100, "max": 250, "default": 170},
    {"key": "weight", "label": "Weight (kg)", "type": "number", "min": 30, "max": 200, "default": 70},
    {"key": "experience", "label": "Experience level", "type": "select", "options": ["Beginner", "Intermediate", "Advanced"], "default": "Beginner"},
    {"key": "activity_level", "label": "Current activity level", "type": "select", "options": ["Sedentary", "Lightly active", "Moderately active", "Very active"], "default": "Lightly active"},
    {"key": "goal", "label": "Main fitness goal", "type": "select", "options": ["Lose weight", "Build muscle", "Maintain weight"], "default": "Build muscle"},
    {"key": "equipment", "label": "Equipment available", "type": "multiselect", "options": ["I work out in a gym", "None (bodyweight only)", "Dumbbells", "Barbell", "Resistance bands", "Machines", "Cardio machines"], "default": ["I work out in a gym"]},
    {"key": "session_length", "label": "Preferred session length (minutes)", "type": "select", "options": ["20", "30", "45", "60"], "default": "45"},
    {"key": "workout_days", "label": "Workout days/week", "type": "number", "min": 1, "max": 7, "default": 3},
    {"key": "injuries", "label": "Injuries/limitations (if any)", "type": "text", "default": "None"},
    {"key": "diet", "label": "Diet preferences/restrictions", "type": "multiselect", "options": ["No restrictions", "Vegetarian", "Vegan", "Gluten-free", "Dairy-free"], "default": ["No restrictions"]},
    {"key": "workout_pref", "label": "Workout preferences", "type": "multiselect", "options": ["Strength", "Cardio", "Mobility", "HIIT", "Circuit", "Flexibility"], "default": ["Strength", "Cardio"]},
]

# ─── Form ──────────────────────────────────────────────────────────────────────
with st.form("planner_form"):
    for q in QUESTIONS:
        if q["type"] == "text":
            st.text_input(q["label"], key=q["key"], value=q["default"])
        elif q["type"] == "number":
            st.number_input(q["label"], min_value=q["min"], max_value=q["max"], key=q["key"], value=q["default"])
        elif q["type"] == "select":
            st.selectbox(q["label"], q["options"], key=q["key"], index=q["options"].index(q["default"]))
        else:
            st.multiselect(q["label"], q["options"], key=q["key"], default=q["default"])
    submitted = st.form_submit_button("🧠 Generate 30-Day Plan")

# ─── Generate Plan & Translation ─────────────────────────────────────────────
if submitted:
    data = {q["key"]: st.session_state[q["key"]] for q in QUESTIONS}
    profile = "\n".join([f"- {q['label']}: {data[q['key']]}" for q in QUESTIONS])

    sys_prompt = (
        "You are a certified personal trainer and nutritionist. "
        "Provide evidence-based, safe, and technical guidance. "
        "Follow accepted standards (e.g. ACSM guidelines, FITT principle, RPE, 1RM when applicable)."
    )
    user_prompt = f"""
Generate a 30-day personalized fitness & meal plan for {data['name']} (Age: {data['age']}, Gender: {data['gender']}, Height: {data['height']} cm, Weight: {data['weight']} kg).
Profile:
{profile}

Requirements:
• Friendly greeting at start (e.g. “Hey Amir!”).
• Workout Days/Week: {data['workout_days']}, Session duration: {data['session_length']} min.
• Experience: {data['experience']}, Activity level: {data['activity_level']}.
• Equipment: {', '.join(data['equipment'])}.
• Injuries: {data['injuries']}.
• Workout Preferences: {', '.join(data['workout_pref'])}.
• Fitness Goal: {data['goal']}.
• Diet: {', '.join(data['diet'])}.

Provide:
1. 🏋️ Workout schedule – daily exercises with sets, reps, rest times, RPE.
2. 🍽️ Daily meals (breakfast, lunch, dinner, snacks) with approximate macros per meal and total daily kcal/protein/carbs/fat.
3. 📊 Weekly macro summary.
4. 📚 Brief evidence-based rationale for exercise and nutrition choices.
5. ⚠️ Safety note: warnings about proper form or consulting a professional if needed.

Format:
- Use headings for each day (e.g. “Day 1”, …).
- Use bullet lists or tables as appropriate.
- Keep tone technical yet approachable.
"""
    with st.spinner("🧠 Letting the expert build your plan..."):
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":sys_prompt},
                      {"role":"user","content":user_prompt}],
            temperature=0.7,
            max_tokens=3000
        )
        st.session_state.plan = response.choices[0].message.content

        # ─── Generate Farsi Translation ─────────────────────────────────
        translation_prompt = (
            "Translate the following plan into Farsi, preserving markdown formatting and style:\n\n" + st.session_state.plan
        )
        farsi_response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a professional translation assistant."},
                      {"role":"user", "content":translation_prompt}],
            temperature=0.7,
            max_tokens=3000
        )
        st.session_state.farsi_plan = farsi_response.choices[0].message.content

# ─── Display Response with Copy Buttons ────────────────────────────────────────
if st.session_state.plan:
    st.subheader(f"📝 {st.session_state.name}, here’s your 30‑Day Expert Plan")

    with st.expander("📋 Click to View & Copy Plan"):
        st.markdown(                f"""
                <div style="
                    background-color: #f1f3f8;
                    padding: 20px;
                    border-radius: 12px;
                    direction: rtl;
                    text-align: left;
                    line-height: 1.8;
                    font-size: 16px;
                ">
                    {st.session_state.plan}
                </div>
                """,
                unsafe_allow_html=True
            )

        # Add a copy button
        copy_button = st.button("📋 Copy Plan", key="copy_button")
        if copy_button:
            pyperclip.copy(st.session_state.plan)
            st.success("Plan copied to clipboard!")

    # Display Farsi plan
    if st.session_state.farsi_plan:
        st.subheader("📝 برنامه ۳۰ روزه به فارسی")
        with st.expander("📋 مشاهده و کپی برنامه فارسی"):
            # Apply RTL styling directly with inline CSS
            st.markdown(
                f"""
                <div style="
                    background-color: #f1f3f8;
                    padding: 20px;
                    border-radius: 12px;
                    direction: rtl;
                    text-align: right;
                    line-height: 1.8;
                    font-size: 16px;
                ">
                    {st.session_state.farsi_plan}
                </div>
                """,
                unsafe_allow_html=True
            )

            copy_button_farsi = st.button("📋 Copy Farsi Plan", key="copy_button_farsi")
            if copy_button_farsi:
                pyperclip.copy(st.session_state.farsi_plan)
                st.success("Farsi plan copied to clipboard!")
