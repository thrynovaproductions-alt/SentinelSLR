import streamlit as st
from google import genai
from PIL import Image, ImageEnhance
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os

# --- 1. SETUP & CONFIGURATION ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)
DB_FILE = "sentinel_slr.db"
CONFIG_FILE = "sentinel_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"version": 2.1, "total_losses": 0.0, "rule_stats": {
            "Avoid chasing vertical moves.": {"wins": 0, "losses": 0},
            "Check RSI for 70+ levels.": {"wins": 0, "losses": 0}
        }}
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

# --- 2. THE REINFORCEMENT LEARNING ENGINE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS slr_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, 
                 verdict_text TEXT, outcome TEXT, rule_applied TEXT,
                 entry_price REAL, target_price REAL, stop_price REAL, 
                 reflection_text TEXT)''')
    conn.commit()
    conn.close()

def automated_audit(current_price):
    """Closes previous trades automatically based on new data."""
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
            config['total_losses'] += abs(trade['entry_price'] - trade['stop_price'])
            updated = True
            p = f"CRITICAL: Financial loss at {current_price}. Diagnose the flaw."
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[p])
            conn.execute("UPDATE slr_log SET reflection_text = ? WHERE id = ?", (res.text, trade['id']))

        if status:
            conn.execute("UPDATE slr_log SET outcome = ? WHERE id = ?", (status, trade['id']))
    
    conn.commit()
    conn.close()
    if updated:
        with open(CONFIG_FILE, 'w') as f: json.dump(config, f)

# --- 3. ANALYST WITH STABILITY PATCHES ---
def process_chart(img_file, best_rule, loss_streak):
    raw_img = Image.open(img_file)
    processed_img = ImageEnhance.Contrast(raw_img).enhance(1.8)
    
    effort = "Deep technical scan. Risk is HIGH." if loss_streak > 0 else "Standard scan."
    prompt = f"{effort} Rule: {best_rule}. Extract PRICE. Return ONLY JSON: {{'verdict': 'BUY/SELL', 'price': float, 'target': float, 'stop': float, 'logic': 'str'}}"
    
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, processed_img])
        
        # STABILITY PATCH: Clean AI response for JSON parsing
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        
        automated_audit(data['price'])
        
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO slr_log (timestamp, verdict_text, rule_applied, entry_price, target_price, stop_price) VALUES (?, ?, ?, ?, ?, ?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M"), data['logic'], best_rule, data['price'], data['target'], data['stop']))
        conn.commit(); conn.close()
        return data
    except Exception as e:
        st.error(f"⚠️ Sentinel Brain Error: {str(e)}")
        return None

# --- 4. UI LAYOUT ---
st.set_page_config(page_title="🛡️ Sentinel SLR", layout="wide")
init_db()

with st.sidebar:
    st.header("⚖️ Risk Monitor")
    config = load_config()
    st.metric("Risk Impact", f"${config['total_losses']:.2f}")
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            st.download_button("📥 Backup DB", f, "sentinel.db")

st.title("🛡️ Sentinel Autonomous Intelligence")
tab1, tab2 = st.tabs(["📸 Scanner", "📊 Audit Log"])

with tab1:
    files = st.file_uploader("Upload Charts", type=["jpg","png","jpeg"], accept_multiple_files=True)
    if files and st.button("🚀 Run Auto-Audit & Predict"):
        best_rule = max(config['rule_stats'], key=lambda x: (config['rule_stats'][x]['wins']+1)/(config['rule_stats'][x]['wins']+config['rule_stats'][x]['losses']+1))
        for f in files:
            res = process_chart(f, best_rule, config['total_losses'])
            if res: st.success(f"Verified {res['verdict']} at {res['price']}")

with tab2:
    st.dataframe(pd.read_sql_query("SELECT * FROM slr_log ORDER BY id DESC", sqlite3.connect(DB_FILE)))
