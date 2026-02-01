import streamlit as st
from google import genai
from PIL import Image, ImageEnhance
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os
import plotly.graph_objects as px

# --- 1. SETUP & CONFIGURATION ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)
DB_FILE = "sentinel_slr.db"
CONFIG_FILE = "sentinel_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"version": 1.3, "rule_stats": {
            "Avoid chasing vertical moves.": {"wins": 0, "losses": 0},
            "Check RSI for 70+ levels.": {"wins": 0, "losses": 0}
        }}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# --- 2. DATABASE & AUTOMATED AUDIT ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS slr_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 timestamp DATETIME, verdict_text TEXT, 
                 outcome TEXT, rule_applied TEXT,
                 entry_price REAL, target_price REAL, stop_price REAL)''')
    conn.commit()
    conn.close()

def automated_audit(current_price):
    """Self-Backtesting: Checks 'Pending' trades against new price data."""
    conn = sqlite3.connect(DB_FILE)
    pending = pd.read_sql_query("SELECT * FROM slr_log WHERE outcome IS NULL", conn)
    config = load_config()
    updated = False

    for _, trade in pending.iterrows():
        status = None
        if current_price >= trade['target_price']:
            status = 'Win ✅'
            config['rule_stats'][trade['rule_applied']]['wins'] += 1
            updated = True
        elif current_price <= trade['stop_price']:
            status = 'Loss ❌'
            config['rule_stats'][trade['rule_applied']]['losses'] += 1
            updated = True
        
        if status:
            conn.execute("UPDATE slr_log SET outcome = ? WHERE id = ?", (status, trade['id']))
    
    conn.commit()
    conn.close()
    if updated: save_config(config)

init_db()

# --- 3. IMAGE ENHANCEMENT ---
def enhance_image(img):
    """Boosts contrast/sharpness for mobile chart readability."""
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    return img

# --- 4. ANALYST ENGINE ---
def render_analyst():
    config = load_config()
    st.caption(f"Sentinel Intelligence v{config['version']}")
    
    input_mode = st.radio("Input Source", ["📸 Camera", "📁 Batch Gallery"], horizontal=True)
    
    if input_mode == "📸 Camera":
        img_files = [st.camera_input("Scanner")]
    else:
        # Multi-upload enabled for batch processing
        img_files = st.file_uploader("Select Charts", 
                                    type=["jpg", "png", "jpeg", "JPG", "PNG", "JPEG"], 
                                    accept_multiple_files=True)
    
    if img_files and any(img_files) and st.button("🚀 Process & Audit"):
        rules = config['rule_stats']
        # Survival of the fittest: Pick the rule with best win rate
        best_rule = max(rules, key=lambda x: (rules[x]['wins']+1)/(rules[x]['wins']+rules[x]['losses']+1))
        
        for uploaded_file in img_files:
            if uploaded_file is None: continue
            
            with st.status(f"Analyzing {getattr(uploaded_file, 'name', 'Camera Stream')}...", expanded=False):
                raw_image = Image.open(uploaded_file)
                processed_image = enhance_image(raw_image)
                
                prompt = f"""Rule: {best_rule}. Analyze this chart.
                Return ONLY JSON: {{"verdict": "BUY/SELL/WAIT", "price": float, "target": float, "stop": float, "confidence": int, "logic": "1 sentence"}}"""
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, processed_image])
                
                try:
                    data = json.loads(response.text)
                    automated_audit(data['price']) # Check past trades before logging new one
                    
                    # Log the new pending trade
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("INSERT INTO slr_log (timestamp, verdict_text, rule_applied, entry_price, target_price, stop_price) VALUES (?, ?, ?, ?, ?, ?)",
                                 (datetime.now().strftime("%Y-%m-%d %H:%M"), data['logic'], best_rule, data['price'], data['target'], data['stop']))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Verdict: {data['verdict']} | Conf: {data['confidence']}%")
                except Exception as e:
                    st.error(f"Error parsing AI response: {e}")

# --- 5. UI & ROUTING ---
st.set_page_config(page_title="🛡️ Sentinel", layout="wide")

with st.sidebar:
    st.header("⚙️ Settings")
    mobile_mode = st.checkbox("📱 Mobile Mode", value=True)
    if st.button("Reset Database"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()

if mobile_mode:
    choice = st.radio("Navigation", ["📸 Analyst", "📊 Audit", "🧠 Stats"], horizontal=True)
    if choice == "📸 Analyst": render_analyst()
    elif choice == "📊 Audit": 
        st.dataframe(pd.read_sql_query("SELECT * FROM slr_log ORDER BY id DESC", sqlite3.connect(DB_FILE)))
else:
    tab1, tab2, tab3 = st.tabs(["📸 Analyst", "📊 Audit", "🧠 Map"])
    with tab1: render_analyst()
