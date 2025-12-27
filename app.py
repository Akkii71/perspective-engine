import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import json
import re

# --- Page Config ---
st.set_page_config(
    page_title="The Perspective Engine",
    page_icon="🧠",
    layout="wide"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .perspective-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border-left: 5px solid #4CAF50;
    }
    .card-title {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 10px;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: Setup ---
st.sidebar.header("⚙️ Settings")

# YOUR API KEY
api_key = st.secrets["AIzaSyALHBKRVHRMMc82-DauM3h9Ht3r4Zlc8bU"]

st.sidebar.markdown("[Get a Free Key Here](https://aistudio.google.com/app/apikey)")
st.sidebar.info(
    "**How it works:**\n"
    "1. Describe a problem.\n"
    "2. Gemini AI analyzes it.\n"
    "3. See your emotions graphed and the situation reframed."
)

# --- Functions ---

def clean_json_string(json_str):
    """
    Cleans JSON string from Markdown formatting and fixes common AI errors.
    """
    # Remove markdown code blocks
    json_str = re.sub(r'```json\n?', '', json_str)
    json_str = re.sub(r'```', '', json_str)
    
    # Attempt to fix "invalid control characters" (newlines inside strings)
    # This removes actual newlines from the string content to prevent crashes
    json_str = json_str.replace('\n', ' ').replace('\r', '')
    
    return json_str.strip()

def get_working_model():
    """
    CRITICAL FIX: This function asks Google for YOUR specific available models.
    It avoids 'Pro' models (which cause 429 errors) and picks the first valid one.
    """
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # 1. Try to find a FREE Flash model first (fastest, no quota issues)
        for m in available_models:
            if 'flash' in m.lower() and '1.5' in m:
                return m
        
        # 2. Fallback to any 'flash' model
        for m in available_models:
            if 'flash' in m.lower():
                return m

        # 3. Fallback to standard 'gemini-pro' (older but reliable)
        for m in available_models:
            if 'gemini-pro' in m:
                return m

        # 4. Emergency: Just return the first one found that isn't the expensive "2.5-pro"
        for m in available_models:
            if "2.5-pro" not in m:
                return m
                
        return "models/gemini-1.5-flash" # Default hope

    except Exception as e:
        st.sidebar.error(f"Could not list models: {e}")
        return "models/gemini-1.5-flash"

def get_ai_response(text, api_key):
    try:
        genai.configure(api_key=api_key)
        
        # --- AUTO-SELECT WORKING MODEL ---
        model_name = get_working_model()
        # ---------------------------------

        model = genai.GenerativeModel(model_name)

        prompt = f"""
        You are an emotional intelligence expert. Analyze the following situation:
        "{text}"

        Return a STRICT JSON object (no other text) with this exact structure. 
        Do not use markdown formatting. Do not use newlines inside string values.
        {{
            "emotions": {{
                "Stress": (integer 0-10),
                "Clarity": (integer 0-10),
                "Frustration": (integer 0-10),
                "Hope": (integer 0-10),
                "Anxiety": (integer 0-10)
            }},
            "perspectives": {{
                "stoic": "Short summary focusing on control.",
                "strategist": "Short bullet-point plan.",
                "compassionate": "Warm, validating response."
            }},
            "one_line_takeaway": "Short philosophical quote."
        }}
        """
        
        # We REMOVE generation_config to avoid strict JSON enforcement causing 404s on older models
        response = model.generate_content(prompt)
        
        clean_text = clean_json_string(response.text)
        return json.loads(clean_text)

    except Exception as e:
        st.error(f"Error with model ({model_name if 'model_name' in locals() else 'unknown'}): {e}")
        st.error("Tip: If you see a '429' error, just wait 30 seconds and try again.")
        return None

def create_radar_chart(emotions):
    categories = list(emotions.keys())
    values = list(emotions.values())
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Current State',
        line_color='#7F7F7F'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )),
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

# --- Main UI ---

st.title("🧠 The Perspective Engine (Fixed)")
st.write("Turn mental chaos into structured clarity using AI.")

user_input = st.text_area("What's on your mind?", height=150, placeholder="e.g., I'm feeling stuck in my coding career...")

if st.button("Reframe My Thoughts ✨"):
    if not api_key:
        st.warning("Please enter your Gemini API Key.")
    elif not user_input:
        st.warning("Please enter some text.")
    else:
        with st.spinner("Analyzing..."):
            data = get_ai_response(user_input, api_key)
        
        if data:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Emotional Radar")
                fig = create_radar_chart(data['emotions'])
                st.plotly_chart(fig, use_container_width=True)
                st.info(f"_{data['one_line_takeaway']}_")

            with col2:
                st.subheader("Cognitive Reframing")
                perspectives = data['perspectives']
                
                # Render Cards
                st.markdown(f"""
                <div class="perspective-card" style="border-left: 5px solid #607D8B;">
                    <div class="card-title">🗿 The Stoic View</div>
                    {perspectives['stoic']}
                </div>
                <div class="perspective-card" style="border-left: 5px solid #2196F3;">
                    <div class="card-title">♟️ The Strategist View</div>
                    {perspectives['strategist']}
                </div>
                <div class="perspective-card" style="border-left: 5px solid #E91E63;">
                    <div class="card-title">❤️ The Compassionate View</div>
                    {perspectives['compassionate']}
                </div>
                """, unsafe_allow_html=True)