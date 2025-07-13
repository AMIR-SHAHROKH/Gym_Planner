import os
from dotenv import load_dotenv
import streamlit as st
import openai
import requests
from fontTools.ttLib import TTFont
from fpdf import FPDF
import tempfile

# ───── Load env and clear proxy env vars ─────
load_dotenv()
for var in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(var, None)

openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not openai.api_key:
    st.error("❌ OpenAI API key not found.")
    st.stop()

# ───── Download the font if not already present ─────
def download_font(font_url, font_name="DejaVuSans.ttf"):
    if not os.path.exists(font_name):
        st.write(f"🔽 Downloading font: {font_name}...")
        try:
            response = requests.get(font_url)
            response.raise_for_status()
            with open(font_name, "wb") as f:
                f.write(response.content)
            # Check if the font is a valid TTF or OTF
            try:
                font = TTFont(font_name)
                font.close()  # Ensure the font is valid
                st.write(f"✅ Font {font_name} downloaded successfully.")
            except Exception as e:
                os.remove(font_name)  # Remove the invalid file
                st.error(f"❌ The downloaded font is not a valid TTF or OTF font. {e}")
                st.stop()
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Failed to download the font: {e}")
            st.stop()

# Proper font URL for DejaVuSans TTF font (known to be valid)
font_url = "https://github.com/dejavu-fonts/dejavu/blob/master/ttf/DejaVuSans.ttf?raw=true"

# Check and download font
download_font(font_url)

# ───── Page & styling ─────
st.set_page_config(page_title="Gym & Meal Planner", layout="centered")
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

# ───── Questions ─────
CORE_QUESTIONS = [
    {"key": "name", "label": "What’s your name?", "type": "text"},
    {"key": "age", "label": "Age", "type": "number", "min": 10, "max": 100, "default": 25},
    {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"]},
    {"key": "height", "label": "Height (cm)", "type": "number", "min": 100, "max": 250, "default": 170},
    {"key": "weight", "label": "Weight (kg)", "type": "number", "min": 30, "max": 200, "default": 80},
    {"key": "activity_level", "label": "Current activity level", "type": "select",
     "options": ["Sedentary", "Lightly active", "Moderately active", "Very active"], "default": "Lightly active"},
    {"key": "goal", "label": "Main fitness goal", "type": "select",
     "options": ["Lose weight", "Build muscle", "Maintain weight"], "default": "Build muscle"},
    {"key": "diet", "label": "Diet preferences/restrictions", "type": "multiselect",
     "options": ["No restrictions", "Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "No pork", "No beef"], "default": ["No restrictions"]},
    {"key": "workout_days", "label": "Days/week you can work out", "type": "number", "min": 1, "max": 7, "default": 3},
]

ADDITIONAL_QUESTIONS = [
    {"key": "experience", "label": "Experience level", "type": "select",
     "options": ["Beginner", "Intermediate", "Advanced"], "default": "Beginner"},
    {"key": "equipment", "label": "Equipment available", "type": "multiselect",
     "options": ["None (bodyweight only)", "Dumbbells", "Barbell", "Resistance bands", "Machines", "Cardio machines"], "default": ["None (bodyweight only)"]},
    {"key": "session_length", "label": "Preferred session length (minutes)", "type": "select",
     "options": ["20", "30", "45", "60"], "default": "30"},
    {"key": "injuries", "label": "Any injuries or limitations?", "type": "text", "default": "None"},
    {"key": "workout_pref", "label": "Workout preferences", "type": "multiselect",
     "options": ["Strength", "Cardio", "Mobility", "HIIT", "Circuit", "Flexibility"], "default": ["Strength"]},
]

QUESTIONS = CORE_QUESTIONS + ADDITIONAL_QUESTIONS

# ───── Session state ─────
if "plan" not in st.session_state:
    st.session_state.plan = None
if "farsi_plan" not in st.session_state:
    st.session_state.farsi_plan = None

# ───── UI ─────
st.title("🏋️‍♂️ Personalized Gym & Meal Planner")
st.markdown("Fill out the form to get a customized 30-day plan.")

with st.form("planner_form"):
    for q in QUESTIONS:
        if q["type"] == "text":
            st.text_input(q["label"], key=q["key"], value=q.get("default", ""))
        elif q["type"] == "number":
            st.number_input(q["label"], min_value=q["min"], max_value=q["max"], key=q["key"], value=q.get("default", q["min"]))
        elif q["type"] == "select":
            default_index = q["options"].index(q.get("default", q["options"][0])) if "default" in q else 0
            st.selectbox(q["label"], q["options"], key=q["key"], index=default_index)
        elif q["type"] == "multiselect":
            st.multiselect(q["label"], q["options"], key=q["key"], default=q.get("default", []))

    submitted = st.form_submit_button("🧠 Generate My 30-Day Plan 🧠")

# ───── Generate Plan ─────
if submitted:
    name = st.session_state.name or "Client"
    details = "\n".join([f"- {q['label']}: {st.session_state[q['key']]}" for q in QUESTIONS if q["key"] != "name"])

    equipment = ", ".join(st.session_state.equipment) if st.session_state.equipment else "None"
    workout_pref = ", ".join(st.session_state.workout_pref) if st.session_state.workout_pref else "None"

    prompt = f"""
You are a motivational fitness coach creating a personalized 30-day gym & meal plan for {name}.

Write in a casual, warm, and friendly style — like you're talking to a good friend.
Avoid robotic, overly formal, or AI-like phrases.
Use encouraging language with a touch of humor or enthusiasm.

Profile:
- Experience: {st.session_state.experience}
- Equipment: {equipment}
- Session Length: {st.session_state.session_length} minutes
- Injuries: {st.session_state.injuries}
- Workout Preferences: {workout_pref}

Details:
{details}

Respond with:
- A friendly greeting
- A daily gym plan with exercises, sets, reps, rest times
- A daily meal plan (breakfast, lunch, dinner, snacks)
- Macronutrient breakdown (calories, protein, carbs, fat)
"""

    with st.spinner("Generating your plan..."):
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a motivational fitness & nutrition expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2500,
        )
        st.session_state.plan = res.choices[0].message.content

# ───── Display Plan ─────
if st.session_state.plan:
    st.markdown(f"## 📝 Hey {st.session_state.name}, here’s your personalized 30-day fitness & meal plan!")

    styled_plan = f"""
    <div style="
        background: #F3E8FF; 
        border-radius: 12px; 
        padding: 20px; 
        box-shadow: 2px 4px 8px rgba(94, 53, 177, 0.2); 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        color: #4A148C;
        white-space: pre-wrap;
        font-size: 16px;
        line-height: 1.5;
        ">
        {st.session_state.plan}
    </div>
    """
    st.markdown(styled_plan, unsafe_allow_html=True)

    # Farsi translation button
    if st.button("📘 نمایش برنامه به فارسی 📘"):
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
