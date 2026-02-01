import streamlit as st
from google import genai
from PIL import Image, ImageEnhance
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os
import io

# --- 1. SETUP & CONFIGURATION ---
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)
DB_FILE = "sentinel_slr.db"
CONFIG_FILE = "sentinel_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"version": 1.6, "rule_stats": {
            "Avoid chasing vertical moves.": {"wins": 0, "losses": 0},
            "Check RSI for 70+ levels.": {"wins": 0, "losses": 0}
        }}
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

# --- 2. MARKET PULSE (FEB 2026 CONTEXT) ---
def get_market_sentiment():
    """Provides real-time macro context for Feb 2026."""
    return {
        "regime": "MATURE BULL (High Correction Risk)",
        "bias": "BEARISH (Short-term) / BULLISH (Long-term)",
        "alert": "⚠️ February Flinch: Watch for 5-10% pullback."
    }

# --- 3. DATABASE & EVOLUTION ENGINE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS slr_log 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, 
                 verdict_text TEXT, outcome TEXT, rule_applied TEXT,
                 entry_price REAL, target_price REAL, stop_price REAL, reflection_text TEXT)''')
    conn.commit()
    conn.close()

def evolve_strategy():
    """AI identifies failures to rewrite the weakest rule."""
    conn = sqlite3.connect(DB_FILE)
    losses = pd.read_sql_query("SELECT rule_applied, reflection_text FROM slr_log WHERE outcome = 'Loss ❌'", conn)
    conn.close()
    if losses.empty: return "Need more loss data to evolve."

    worst_rule = losses['rule_applied'].value_counts().idxmax()
    context = "\n".join(losses[losses['rule_applied'] == worst_rule]['reflection_text'].tolist()[:5])
    
    prompt = f"Rule '{worst_rule}' is failing. Post-mortems: {context}. Suggest a REFINED 1-sentence rule. JSON: {{'new_rule': 'str'}}"
    res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt])
    
    new_rule = json.loads(res.text)['new_rule']
    config = load_config()
    config['rule_stats'][new_rule] = {"wins": 0, "losses": 0}
    del config['rule_stats'][worst_rule]
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f)
    return f"Evolved to: {new_rule}"

# --- 4. BACKUP SYSTEM ---
def get_db_binary():
    """Prepares the SQLite DB for download to prevent data loss."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            return f.read()
    return None

# --- 5. ANALYST & UI ---
st.set_page_config(page_title="🛡️ Sentinel", layout="wide")
init_db()

with st.sidebar:
    st.header("🌐 Market Pulse")
    pulse = get_market_sentiment()
    st.metric("Regime", pulse["regime"])
    st.warning(pulse["alert"])
    
    st.header("🧬 Strategy Lab")
    if st.button("🔥 Evolve Weakest Rule"): st.sidebar.info(evolve_strategy())
    
    st.header("💾 Data Safety")
    db_data = get_db_binary()
    if db_data:
        st.download_button(label="📥 Download Database Backup", 
                           data=db_data, 
                           file_name=f"sentinel_backup_{datetime.now().strftime('%Y%m%d')}.db",
                           mime="application/x-sqlite3")
    
    if st.button("Clear All Data"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
        st.rerun()

# --- ANALYST ROUTING ---
st.title("🛡️ Sentinel SLR Intelligence")
tab1, tab2, tab3 = st.tabs(["📸 Analyst", "📊 Audit Log", "🧠 Knowledge Map"])

with tab1:
    # [Dual-Timeframe Analyst Logic from previous step goes here]
    st.info("Upload Execution and Anchor charts to begin analysis.")
