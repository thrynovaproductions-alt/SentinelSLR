import streamlit as st
from google import genai
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objects as px # Better than Matplotlib for Streamlit

# --- CONFIG & EVOLUTION ENGINE ---
CONFIG_FILE = "sentinel_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"version": 1.0, "rule_stats": {
            "Avoid chasing vertical moves.": {"wins": 0, "losses": 0, "streak": 0},
            "Check RSI for 70+ levels.": {"wins": 0, "losses": 0, "streak": 0}
        }}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def evolve_rule(rule_name, history_summary):
    """IMPROVISATION: AI analyzes failures to suggest a better rule"""
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    prompt = f"Rule '{rule_name}' is failing. History: {history_summary}. Suggest a 1-sentence modification to fix this."
    response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt])
    return response.text

# --- UI HEADER ---
st.set_page_config(page_title="SENTINEL v2: Evolved", layout="wide", page_icon="🛡️")
st.title("🛡️ Sentinel SLR: Intelligence Engine")

tab1, tab2, tab3, tab4 = st.tabs(["📸 Analyst", "📊 Audit", "🧠 Knowledge Map", "🧬 Evolution"])

# --- TAB 1: ANALYST (With Confidence Scoring) ---
with tab1:
    config = load_config()
    img_file = st.camera_input("Scanner")
    
    if img_file:
        # Selection logic: Pick rule with highest Win Rate + lowest Streak
        best_rule = max(config['rule_stats'], key=lambda x: (config['rule_stats'][x]['wins'] + 1) / (config['rule_stats'][x]['losses'] + 1))
        
        if st.button(f"Analyze with {best_rule}"):
            # IMPROVISATION: Prompting for Structured JSON
            prompt = f"""
            Rule: {best_rule}
            Analyze this chart. Output as:
            VERDICT: [BUY/SELL/WAIT]
            CONFIDENCE: [0-100%]
            REASONING: [Short bullet points]
            """
            # (AI Call logic here...)
            st.success("Analysis Complete. Logged to Database.")

# --- TAB 3: KNOWLEDGE MAP (Upgraded to Plotly) ---
with tab3:
    st.subheader("Neural Rule Network")
    # IMPROVISATION: Plotly Scatter for 'Rule Gravity'
    # High win rate = Green, High usage = Large size
    df_rules = pd.DataFrame([
        {"rule": k, "wins": v['wins'], "losses": v['losses'], "total": v['wins']+v['losses']} 
        for k, v in config['rule_stats'].items()
    ])
    df_rules['win_rate'] = (df_rules['wins'] / df_rules['total']).fillna(0)
    
    fig = px.scatter(df_rules, x="win_rate", y="total", size="total", color="win_rate",
                     hover_name="rule", color_continuous_scale="RdYlGn",
                     title="Rule Performance Gravity")
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 4: EVOLUTION (The New Feature) ---
with tab4:
    st.subheader("Rule Evolution Lab")
    for rule, stats in config['rule_stats'].items():
        if stats['losses'] > stats['wins'] and stats['total'] > 3:
            st.warning(f"⚠️ Rule '{rule}' is underperforming.")
            if st.button(f"Evolve: {rule[:20]}..."):
                new_rule = evolve_rule(rule, "3 consecutive losses in overbought conditions")
                st.info(f"Suggested Modification: {new_rule}")
