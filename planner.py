import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import streamlit as st
import openai

# 0. DISABLE PROXY ENV VARS (avoid httpx proxy errors)
for var in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(var, None)

# 1. SET YOUR API KEY
openai.api_key = os.getenv("OPENAI_API_KEY", None)
if not openai.api_key:
    st.error("OpenAI API key not found. Please set it in your .env file or environment.")
    st.stop()

# 2. QUESTIONS TO PERSONALIZE THE PLAN
QUESTIONS = [
    {"key": "age", "label": "Age", "type": "number", "min": 10, "max": 100},
    {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"]},
    {"key": "height", "label": "Height (cm)", "type": "number", "min": 100, "max": 250},
    {"key": "weight", "label": "Weight (kg)", "type": "number", "min": 30, "max": 200},
    {"key": "activity_level", "label": "Activity Level", "type": "select", "options": [
        "Sedentary (little to no exercise)",
        "Lightly Active (1–3 days/week)",
        "Moderately Active (3–5 days/week)",
        "Very Active (6–7 days/week)",
    ]},
    {"key": "goal", "label": "Primary Goal", "type": "select", "options": ["Lose Weight", "Build Muscle", "Maintain Weight"]},
    {"key": "diet", "label": "Dietary Preferences / Restrictions", "type": "multiselect", "options": [
        "No Restrictions", "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "No Pork", "No Beef",
    ]},
    {"key": "workout_days", "label": "Workout Days per Week", "type": "number", "min": 1, "max": 7},
]

# 3. SESSION STATE INITIALIZATION
if 'plan' not in st.session_state:
    st.session_state.plan = None
if 'farsi_plan' not in st.session_state:
    st.session_state.farsi_plan = None

# 4. PAGE LAYOUT
st.title("🏋️ Gym & 🍎 Meal Planner Bot")
st.markdown("Answer the questions below to get your customized 30-day gym and meal plan.")

# 5. INPUT FORM
with st.form(key='planner_form'):
    for q in QUESTIONS:
        if q['type'] == 'number':
            st.number_input(
                q['label'], min_value=q['min'], max_value=q['max'], key=q['key']
            )
        elif q['type'] == 'select':
            st.selectbox(
                q['label'], q['options'], key=q['key']
            )
        elif q['type'] == 'multiselect':
            st.multiselect(
                q['label'], q['options'], key=q['key']
            )
    submitted = st.form_submit_button("Generate My 30-Day Plan")

    if submitted:
        details = "\n".join([
            f"- {q['label']}: {st.session_state[q['key']]}" for q in QUESTIONS
        ])
        prompt = (
            f"You are a certified personal trainer and nutritionist.\n"
            f"Client details:\n{details}\n\n"
            "Please provide:\n"
            "1. A daily gym workout plan for 30 days (exercises, sets, reps, rest).\n"
            "2. A daily meal plan for 30 days (breakfast, lunch, dinner, snacks).\n"
            "3. Total daily macros (calories, protein, carbs, fats)."
        )
        with st.spinner("Generating your personalized 30-day plan..."):
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2500,
            )
            st.session_state.plan = response.choices[0].message.content
            st.session_state.farsi_plan = None

# 6. DISPLAY AND TRANSLATION
if st.session_state.plan:
    st.markdown("## 📝 Your 30-Day Plan")
    st.markdown(st.session_state.plan)
    if st.button("نمایش برنامه به فارسی"):
        if not st.session_state.farsi_plan:
            with st.spinner("در حال ترجمه..."):
                trans_resp = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant translating English to Farsi."},
                        {"role": "user", "content": (
                            "Translate the following fitness and meal plan into Persian (Farsi):\n\n"
                            f"{st.session_state.plan}"
                        )},
                    ],
                    temperature=0.3,
                    max_tokens=2500,
                )
                st.session_state.farsi_plan = trans_resp.choices[0].message.content
        st.markdown("## 📝 برنامه ۳۰ روزه به فارسی")
        st.markdown(st.session_state.farsi_plan)
