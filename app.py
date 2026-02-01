import streamlit as st
from google import genai
import sqlite3
import pandas as pd
from PIL import Image
from datetime import datetime
import json
import os
import plotly.graph_objects as px

# --- SECRETS & CONFIG ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)
DB_FILE = "sentinel_slr.db"
CONFIG_FILE = "sentinel_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"version": 1.1, "mobile_mode": False, "rule_stats": {
            "Avoid chasing vertical moves.": {"wins": 0, "losses": 0},
            "Check RSI for 70+ levels.": {"wins": 0, "losses": 0}
        }}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# --- UI SETTINGS ---
st.set_page_config(page_title="🛡️ Sentinel", layout="wide")

# Persistent Mobile Toggle in Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    mobile_mode = st.checkbox("📱 Mobile Mode", value=False)
    st.info("Mobile Mode collapses headers and prioritizes the scanner.")

# --- APP TABS ---
if mobile_mode:
    # Simplified Mobile View: No tabs, just vertical flow
    st.title("🛡️ Sentinel Mobile")
    tab_list = ["📸 Analyst", "📊 Audit", "🧠 Stats"]
    choice = st.radio("Navigation", tab_list, horizontal=True)
else:
    st.title("🛡️ Evolved Sentinel SLR")
    tab1, tab2, tab3 = st.tabs(["📸 Analyst", "📊 Audit", "🧠 Knowledge Map"])
    choice = None

# --- LOGIC SECTIONS ---
def render_analyst():
    config = load_config()
    st.caption(f"v{config['version']}")
    
    # Use camera_input for mobile-first experience
    img_file = st.camera_input("Capture Chart")
    
    if img_file and st.button("🚀 Analyze"):
        rules = config['rule_stats']
        best_rule = max(rules, key=lambda x: (rules[x]['wins'] + 1) / (rules[x]['wins'] + rules[x]['losses'] + 1))
        
        with st.spinner("Sentinel Brain Analyzing..."):
            image = Image.open(img_file)
            prompt = f"Rule: {best_rule}\nAnalyze this chart. Provide Verdict, Confidence %, and Levels."
            response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, image])
            
            st.markdown("### 🛡️ Verdict")
            st.write(response.text)

# --- ROUTING ---
if mobile_mode:
    if choice == "📸 Analyst": render_analyst()
    elif choice == "📊 Audit": st.write("Audit Mode Active") # Add your audit logic here
    else: st.write("Stats View")
else:
    with tab1: render_analyst()
    with tab2: st.write("Audit Tab Active")
    with tab3: st.write("Map Tab Active")
