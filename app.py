import streamlit as st
from google import genai
import sqlite3
import pandas as pd
from PIL import Image
from datetime import datetime
import json
import os
import plotly.graph_objects as px

# 1. SETUP & CONFIGURATION
# Access secrets securely in the cloud
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

DB_FILE = "sentinel_slr.db"
CONFIG_FILE = "sentinel_config.json"

DEFAULT_CONFIG = {
    "version": 1.1,
    "rule_stats": {
        "Avoid chasing vertical moves.": {"wins": 0, "losses": 0},
        "Check RSI for 70+ levels.": {"wins": 0, "losses": 0}
    }
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# 2. DATABASE INITIALIZATION
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS slr_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 timestamp DATETIME, verdict_text TEXT, 
                 outcome TEXT, rule_applied TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 3. UI LAYOUT
st.set_page_config(page_title="🛡️ Evolved Sentinel", layout="wide")
tab1, tab2, tab3 = st.tabs(["📸 Analyst", "📊 Audit", "🧠 Knowledge Map"])

# --- TAB 1: ANALYST ---
with tab1:
    config = load_config()
    st.caption(f"Intelligence v{config['version']}")
    img_file = st.file_uploader("Upload or Capture Chart", type=['jpg', 'png', 'jpeg'])

    if img_file and st.button("🚀 Analyze"):
        # Selection logic for best rule
        rules = config['rule_stats']
        best_rule = max(rules, key=lambda x: (rules[x]['wins'] + 1) / (rules[x]['wins'] + rules[x]['losses'] + 1))
        
        image = Image.open(img_file)
        prompt = f"System Rule: {best_rule}\nAnalyze this chart in the Sentinel Verdict format."
        
        # Call Gemini
        response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, image])
        st.markdown(response.text)

        # Log to DB
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO slr_log (timestamp, verdict_text, rule_applied) VALUES (?, ?, ?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M"), response.text, best_rule))
        conn.commit()
        conn.close()

# --- TAB 3: KNOWLEDGE MAP ---
with tab3:
    st.subheader("Performance Gravity")
    df_rules = pd.DataFrame([
        {"rule": k, "wins": v['wins'], "losses": v['losses'], "total": v['wins']+v['losses']} 
        for k, v in config['rule_stats'].items()
    ])
    df_rules['win_rate'] = (df_rules['wins'] / df_rules['total']).fillna(0)
    
    # Modern Plotly visualization
    fig = px.scatter(df_rules, x="win_rate", y="total", size="total", color="win_rate",
                     hover_name="rule", color_continuous_scale="RdYlGn",
                     range_x=[0, 1])
    st.plotly_chart(fig, use_container_width=True)
