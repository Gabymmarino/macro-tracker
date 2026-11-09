import html
import json
import os
import re
import urllib.parse
from datetime import datetime

import altair as alt
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# --- CONFIGURATION ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-3.8-flash')

DATA_FILE = "nutrition_data.json"

st.set_page_config(page_title="MacroAI", layout="centered", initial_sidebar_state="expanded")

# --- WHOOP DESIGN TOKENS ---
BG = "#14171b"
BG_GRADIENT = (
    "linear-gradient(180deg, #2a3238 0%, #242c31 12%, #21282d 20%, #1c2226 31%, "
    "#171c20 43%, #14171b 59%, #111517 74%, #101215 100%)"
)
LINE = "#2b2f33"
LINE_STRONG = "#3d4247"
TRACK = "#34383c"
MUTED = "#8f9393"
FAINT = "#5f6468"
TEXT = "#ffffff"
GREEN = "#6CE844"
YELLOW = "#F8DC48"
RED = "#E83034"
BLUE = "#4090E0"
MINT = "#6CECA4"
ORANGE = "#F0A844"

FONT_UI = "'Plus Jakarta Sans', 'Figtree', 'Helvetica Neue', Arial, sans-serif"
FONT_NUM = "'DINPro', 'DIN Pro', 'Barlow', 'Arial Narrow', sans-serif"
CHART_FONT = "Barlow"

# --- SVG ICONS ---
PATHS = {
    "menu": "M3 12h18 M3 6h18 M3 18h18",
    "log": "M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z M12 6h5 M12 10h5 M12 14h5",
    "daily": "M7 18a5 5 0 0 1 10 0 M2 18h20 M18 10v4 M16 12l2 2 2-2",
    "weekly": "M12 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4z M12 8v4 M8 12l-4-2 M12 12l4-2 M12 12v6l-4 4 M12 18l4 4",
    "monthly": "M12 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M14 6l-2-2-4 4 2 2 M12 10l-4-4 M12 10v6l-4 4 M12 16l4 4 M8 20h8",
    "goals": "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z",
    "ask": "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
    "flame": "M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z",
}

def get_svg(path_data, stroke=MUTED, fill="none"):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round"><path d="{path_data}"/></svg>'
    )
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)

icon_menu = get_svg(PATHS["menu"], stroke=TEXT)
icon_flame = get_svg(PATHS["flame"], stroke=ORANGE)

NAV = [
    ("LOG MEAL", "nav_log_meal", PATHS["log"]),
    ("DAILY SUMMARY", "nav_daily_summary", PATHS["daily"]),
    ("WEEKLY OVERVIEW", "nav_weekly_overview", PATHS["weekly"]),
    ("MONTHLY OVERVIEW", "nav_monthly_overview", PATHS["monthly"]),
    ("GOALS", "nav_goals", PATHS["goals"]),
    ("ASK", "nav_ask", PATHS["ask"]),
]

# --- DATA MANAGEMENT ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()
today_str = datetime.now().strftime("%Y-%m-%d")

if "goals" not in data:
    data["goals"] = {
        "current_weight": 65.0, "desired_weight": 65.0,
        "target_protein": 130, "target_carbs": 200, "target_fats": 60
    }
if today_str not in data:
    data[today_str] = {"meals": [], "target_burn": 2200}

# --- NAVIGATION STATE ---
if 'page' not in st.session_state:
    st.session_state.page = "LOG MEAL"

def go_to(page_name):
    st.session_state.page = page_name

page = st.session_state.page

# --- STYLES ---
ROOT_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Barlow:wght@500;600;700&display=swap');

:root {{
    --bg: {BG};
    --bg-gradient: {BG_GRADIENT};
    --line: {LINE};
    --line-strong: {LINE_STRONG};
    --track: {TRACK};
    --muted: {MUTED};
    --faint: {FAINT};
    --text: {TEXT};
    --green: {GREEN};
    --yellow: {YELLOW};
    --red: {RED};
    --blue: {BLUE};
    --font-ui: {FONT_UI};
    --font-num: {FONT_NUM};
}}
"""

STATIC_CSS = """
html, body { background: var(--bg) !important; color: var(--text); }
.stApp, [data-testid="stApp"], [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stBottom"] {
    background: var(--bg-gradient) fixed !important;
    color: var(--text);
}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stSidebarHeader"],
[data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {
    background: transparent !important; background-color: transparent !important;
}
:where(.stApp, .stApp *:not([data-testid="stIconMaterial"])) { font-family: var(--font-ui) !important; }
[data-testid="stMainBlockContainer"], .block-container { padding-top: 3rem !important; }

#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] { display: none !important; }

[data-testid="stSidebar"] { border-right: none !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.15rem !important; }
.menu-head { display: flex; justify-content: space-between; align-items: center; padding-bottom: 18px; }
.menu-title { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 13px; letter-spacing: 0.1em; }
.menu-collapse { color: var(--muted); font-size: 16px; }

[data-testid="stSidebar"] [class*="st-key-nav_"] button {
    background: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important;
    min-height: 0 !important; width: 100% !important; padding: 11px 0 !important; display: flex !important;
    align-items: center !important; justify-content: flex-start !important; transition: color 0.15s ease;
}
[data-testid="stSidebar"] [class*="st-key-nav_"] button p { font-size: 13px !important; font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase; margin: 0 !important; color: inherit !important; }
[data-testid="stSidebar"] [class*="st-key-nav_"] button::before { display: block; height: 22px; margin-right: 16px; }
[data-testid="stSidebar"] [class*="st-key-nav_"] button:hover { color: #ffffff !important; }

.page-title { display: flex; align-items: center; gap: 12px; font-weight: 700; font-size: 16px; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 24px; }
.section-title { font-weight: 700; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin: 28px 0 14px 0; }
.hero-label { display: flex; justify-content: center; align-items: center; gap: 6px; color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px; }
.status { text-align: center; font-weight: 700; font-size: 28px; letter-spacing: 0.1em; text-transform: uppercase; margin: 6px 0 24px 0; }
.notice { font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 14px; }
.num { font-family: var(--font-num) !important; }

.macro { margin-bottom: 22px; }
.macro-head { display: flex; justify-content: space-between; align-items: baseline; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 8px; }
.macro-head strong { color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: 0; }
.macro-track { width: 100%; height: 4px; border-radius: 2px; background: var(--track); }
.macro-fill { height: 100%; border-radius: 2px; }

.meal-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding: 14px 0; border-bottom: 1px solid var(--line); }
.meal-name { font-weight: 700; font-size: 14px; letter-spacing: 0.1em; text-transform: uppercase; }
.meal-when { color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: 0.1em; margin-top: 4px; }
.meal-desc { color: var(--muted); font-size: 13px; font-weight: 600; margin-top: 6px; }
.meal-nums { text-align: right; white-space: nowrap; }
.meal-kcal { font-size: 24px; font-weight: 700; }
.meal-unit { color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: 0.1em; }
.meal-macros { color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: 0.1em; margin-top: 2px; }

[data-testid="stMetric"], div[data-testid="metric-container"] { background: transparent !important; border: none !important; box-shadow: none !important; padding: 4px 0 !important; }
[data-testid="stMetricLabel"] *, div[data-testid="metric-container"] label { color: var(--muted) !important; font-size: 11px !important; font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase; }
[data-testid="stMetricValue"] * { font-family: var(--font-num) !important; font-size: 34px !important; font-weight: 700 !important; color: #ffffff !important; }

[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"], [data-testid="stTextAreaRootElement"] { background: transparent !important; background-color: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important; }
.stApp input[type="number"], .stApp input[type="text"] { background: transparent !important; color: #ffffff !important; border: none !important; border-bottom: 1px solid var(--line-strong) !important; border-radius: 0 !important; box-shadow: none !important; padding-left: 0 !important; font-weight: 700 !important; }
.stApp input[type="text"] { font-size: 16px !important; font-weight: 600 !important; }
.stApp input[type="number"] { font-family: var(--font-num) !important; font-size: 28px !important; }
.stApp input:focus { border-bottom-color: #ffffff !important; }
.stApp input::placeholder { color: var(--faint) !important; }
[data-testid="stNumberInput"] button { background: transparent !important; border: none !important; color: var(--muted) !important; }
[data-testid="stNumberInput"] button:hover { color: #ffffff !important; }
[data-testid="stWidgetLabel"] label { color: var(--muted) !important; font-size: 11px !important; font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase; }
[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }

/* ZERO BORDERS FOR FILE UPLOADER */
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section { background: transparent !important; border: none !important; border-radius: 0 !important; padding-left: 0 !important; padding-right: 0 !important; }
[data-testid="stFileUploaderDropzone"] button { background: transparent !important; border: none !important; color: #ffffff !important; padding: 0 !important; box-shadow: none !important; }
[data-testid="stFileUploaderDropzone"] small, [data-testid="stFileUploaderDropzoneInstructions"] * { color: var(--muted) !important; font-size: 11px !important; letter-spacing: 0.05em; }

[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button { background: transparent !important; color: #ffffff !important; border: 1px solid var(--line-strong) !important; border-radius: 10px !important; padding: 10px 18px !important; font-size: 12px !important; font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase; }
[data-testid="stButton"] button:hover { background: transparent !important; border-color: #ffffff !important; }

/* Radio button styling */
[data-testid="stRadio"] label { color: var(--text) !important; font-weight: 700 !important; font-size: 12px !important; letter-spacing: 0.05em !important; }

button[kind="primary"], button[data-testid="stBaseButton-primary"] { background: linear-gradient(90deg, #373059 0%, #29405c 100%) !important; border: none !important; border-radius: 12px !important; color: #ffffff !important; padding: 16px 20px !important; width: 100%; display: flex !important; justify-content: space-between !important; align-items: center !important; }
button[kind="primary"]::after { content: "\\203A"; font-size: 26px; line-height: 1; color: var(--muted); }
button[kind="primary"] p { font-size: 15px !important; letter-spacing: 0.02em !important; }

[data-testid="stChatMessage"] { background: transparent !important; padding: 14px 0 !important; border-bottom: 1px solid var(--line); }
[data-testid="stChatInput"], [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] button { background: transparent !important; box-shadow: none !important; border: none !important; color: #ffffff !important; }
[data-testid="stChatInput"] { border-bottom: 1px solid var(--line-strong) !important; }
"""

def nav_css(active_page):
    rules = []
    for name, key, path in NAV:
        color = TEXT if name == active_page else MUTED
        rules.append(f"[data-testid='stSidebar'] .st-key-{key} button {{ color: {color} !important; }}")
        rules.append(f"[data-testid='stSidebar'] .st-key-{key} button::before {{ content: url('{get_svg(path, stroke=color)}'); }}")
    return "\n".join(rules)

st.markdown(ROOT_CSS + STATIC_CSS + nav_css(page) + "</style>", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.markdown(f"<div class='menu-head'><div class='menu-title'><img src='{icon_menu}' width='24'> MENU</div><div class='menu-collapse'>«</div></div>", unsafe_allow_html=True)
for _name, _key, _ in NAV:
    st.sidebar.button(_name, key=_key, on_click=go_to, args=(_name,))

# --- HELPER FUNCTIONS ---
def page_title(text, icon_path):
    st.markdown(f"<div class='page-title'><img src='{get_svg(icon_path, stroke=TEXT)}' width='22'> {text}</div>", unsafe_allow_html=True)

def notice(text, color=MUTED):
    st.markdown(f"<div class='notice' style='color:{color};'>{text}</div>", unsafe_allow_html=True)

def custom_progress_line(label, current, target, color=TEXT):
    pct = min(current / target, 1.0) * 100 if target > 0 else 0
    st.markdown(
        f"<div class='macro'><div class='macro-head'><span>{label}</span><span><strong class='num'>{int(current)}</strong> / {int(target)}G</span></div>"
        f"<div class='macro-track'><div class='macro-fill' style='width:{pct}%; background:{color};'></div></div></div>",
        unsafe_allow_html=True,
    )

def to_number(value):
    if isinstance(value, (int, float)): return round(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return round(float(match.group())) if match else 0

def analyze_meal_with_gemini(image, description):
    description = description.strip()
    json_format = 'Respond strictly in JSON format with exact keys: {"calories": 0, "protein": 0, "carbs": 0, "fats": 0, "added_sugars": 0, "meal_name": "Short Name"}.'
    if image is not None:
        prompt = f"Analyze this meal photo. User description: '{description or 'none'}'. {json_format}"
        parts = [prompt, image]
    else:
        prompt = f"Estimate the nutrition of this meal from the user's description: '{description}'. {json_format}"
        parts = [prompt]
    try:
        response = model.generate_content(parts)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        raw = json.loads(clean_text)
        return {
            "calories": to_number(raw.get("calories", 0)),
            "protein": to_number(raw.get("protein", 0)),
            "carbs": to_number(raw.get("carbs", 0)),
            "fats": to_number(raw.get("fats", 0)),
            "added_sugars": to_number(raw.get("added_sugars", 0)),
            "meal_name": str(raw.get("meal_name") or description[:40] or "Meal"),
        }
    except Exception as e:
        notice(f"FAILED TO ANALYZE: {html.escape(str(e))}", RED)
        return None

def get_dataframe(days):
    records = []
    for date_key, day_data in data.items():
        if date_key == "goals": continue
        consumed = sum(m.get("calories", 0) for m in day_data.get("meals", []))
        burned = day_data.get("target_burn", 2200)
        records.append({
            "Date": pd.to_datetime(date_key), "Consumed": consumed, "Burned": burned, "Net_Calories": consumed - burned,
            "Protein": sum(m.get("protein", 0) for m in day_data.get("meals", [])),
            "Carbs": sum(m.get("carbs", 0) for m in day_data.get("meals", [])),
            "Fats": sum(m.get("fats", 0) for m in day_data.get("meals", [])),
            "Sugars": sum(m.get("added_sugars", 0) for m in day_data.get("meals", []))
        })
    if not records: return pd.DataFrame()
    df = pd.DataFrame(records).set_index("Date").sort_index()
    return df[df.index >= pd.Timestamp.now() - pd.Timedelta(days=days)].copy()

def format_when(logged_at, fallback_date=None):
    try:
        if logged_at: return datetime.strptime(logged_at, "%Y-%m-%d %H:%M").strftime("%d %b %Y, %H:%M").upper()
        return datetime.strptime(fallback_date, "%Y-%m-%d").strftime("%d %b %Y").upper()
    except (TypeError, ValueError): return ""

def recent_meals(limit=10):
    entries = []
    for date_key, day in data.items():
        if date_key == "goals": continue
        for i, m in enumerate(day.get("meals", [])):
            entries.append((m.get("logged_at") or f"{date_key} 00:00", i, date_key, m))
    entries.sort(key=lambda e: (e[0], e[1]), reverse=True)
    return [(date_key, m) for _, _, date_key, m in entries[:limit]]

def render_meals(entries, show_date=True):
    if not entries:
        notice("NO MEALS LOGGED YET.")
        return
    rows = []
    for date_key, m in entries:
        logged_at = m.get("logged_at")
        when = format_when(logged_at, date_key) if show_date else (logged_at[11:] if logged_at else "")
        name = html.escape(str(m.get("meal_name", "Meal")).upper())
        desc = html.escape(str(m.get("description", ""))[:90])
        rows.append(
            f"<div class='meal-row'><div class='meal-main'><div class='meal-name'>{name}</div>"
            f"<div class='meal-when'>{when}</div>" + (f"<div class='meal-desc'>{desc}</div>" if desc else "") + "</div>"
            f"<div class='meal-nums'><span class='num meal-kcal'>{m.get('calories', 0)}</span> <span class='meal-unit'>KCAL</span>"
            f"<div class='meal-macros'>P {m.get('protein', 0)} &nbsp; C {m.get('carbs', 0)} &nbsp; F {m.get('fats', 0)}</div></div></div>"
        )
    st.markdown("".join(rows), unsafe_allow_html=True)

# --- PAGES ---
if page == "LOG MEAL":
    page_title(f"LOG A MEAL &nbsp;•&nbsp; {format_when(None, today_str)}", PATHS["log"])

    if "form_n" not in st.session_state: st.session_state.form_n = 0
    n = st.session_state.form_n

    if "flash" in st.session_state:
        flash_text, flash_color = st.session_state.pop("flash")
        notice(flash_text, flash_color)

    # Input Mode Selection: AI Analysis or Manual Entry
    input_mode = st.radio("LOGGING METHOD", ["AI PHOTO / TEXT ANALYSIS", "MANUAL ENTRY"], horizontal=True, label_visibility="collapsed")
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    if input_mode == "AI PHOTO / TEXT ANALYSIS":
        img_file = st.file_uploader("PHOTO (OPTIONAL)", type=['jpg', 'jpeg', 'png'], key=f"meal_photo_{n}")
        meal_desc = st.text_input("DESCRIPTION (OPTIONAL IF YOU ADD A PHOTO)", placeholder="...", key=f"meal_desc_{n}")

        if st.button("ANALYZE & LOG", key="log_btn"):
            if not img_file and not meal_desc.strip():
                notice("ADD A PHOTO, A DESCRIPTION, OR BOTH.", RED)
            else:
                with st.spinner("ANALYZING..."):
                    image = Image.open(img_file) if img_file else None
                    result = analyze_meal_with_gemini(image, meal_desc)
                if result:
                    result["logged_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    result["description"] = meal_desc.strip()
                    data[today_str]["meals"].append(result)
                    save_data(data)
                    st.session_state.flash = (f"LOGGED {html.escape(result['meal_name'].upper())}", MINT)
                    st.session_state.form_n += 1
                    st.rerun()
    else:
        with st.form(f"manual_form_{n}"):
            manual_name = st.text_input("MEAL NAME", placeholder="e.g. Chicken & Rice")
            m_cal = st.number_input("CALORIES (KCAL)", min_value=0, value=500, step=10)
            c1, c2, c3, c4 = st.columns(4)
            m_pro = c1.number_input("PROTEIN (G)", min_value=0, value=30, step=5)
            m_carb = c2.number_input("CARBS (G)", min_value=0, value=40, step=5)
            m_fat = c3.number_input("FATS (G)", min_value=0, value=15, step=5)
            m_sug = c4.number_input("SUGARS (G)", min_value=0, value=0, step=1)

            if st.form_submit_button("SAVE MANUAL MEAL"):
                new_meal = {
                    "calories": int(m_cal),
                    "protein": int(m_pro),
                    "carbs": int(m_carb),
                    "fats": int(m_fat),
                    "added_sugars": int(m_sug),
                    "meal_name": manual_name.strip() or "Manual Meal",
                    "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "description": "Manual entry",
                }
                data[today_str]["meals"].append(new_meal)
                save_data(data)
                st.session_state.flash = (f"LOGGED {html.escape(new_meal['meal_name'].upper())}", MINT)
                st.session_state.form_n += 1
                st.rerun()

    st.markdown("<div class='section-title'>RECENT MEALS</div>", unsafe_allow_html=True)
    render_meals(recent_meals())

elif page == "DAILY SUMMARY":
    page_title(f"MY DAY &nbsp;•&nbsp; {format_when(None, today_str)}", PATHS["daily"])

    st.markdown("""<style>.stApp [data-testid="stNumberInput"] { max-width: 280px; margin: 0 auto; } .stApp [data-testid="stNumberInput"] input[type="number"] { text-align: center; font-size: 48px !important; }</style>""", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-label'><img src='{icon_flame}' width='14'> CALORIES BURNED TODAY</div>", unsafe_allow_html=True)
    
    target_burn = st.number_input("CAL", value=data[today_str]["target_burn"], step=50, label_visibility="collapsed")
    data[today_str]["target_burn"] = target_burn
    save_data(data)

    meals = data[today_str]["meals"]
    t_cons = sum(m["calories"] for m in meals)
    diff = t_cons - target_burn

    status = "SURPLUS" if diff > 0 else "DEFICIT" if diff < 0 else "MAINTENANCE"
    status_color = RED if diff > 0 else GREEN if diff < 0 else TEXT
    st.markdown(f"<div class='status' style='color:{status_color};'>{status}</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("BURNED", target_burn)
    c2.metric("CONSUMED", t_cons)
    c3.metric("NET KCAL", f"{diff:+}")

    st.markdown("<div class='section-title'>MACROS</div>", unsafe_allow_html=True)
    custom_progress_line("PROTEIN", sum(m["protein"] for m in meals), data['goals']['target_protein'], GREEN)
    custom_progress_line("CARBOHYDRATES", sum(m["carbs"] for m in meals), data['goals']['target_carbs'], BLUE)
    custom_progress_line("FATS", sum(m["fats"] for m in meals), data['goals']['target_fats'], YELLOW)

    st.markdown(f"<div class='section-title'>TODAY'S MEALS, {format_when(None, today_str)}</div>", unsafe_allow_html=True)
    render_meals([(today_str, m) for m in reversed(meals)], show_date=False)

elif page == "WEEKLY OVERVIEW":
    page_title("WEEKLY OVERVIEW", PATHS["weekly"])
    df = get_dataframe(7)

    if df.empty: notice("NO DATA TO DISPLAY.")
    else:
        df['Color'] = df['Net_Calories'].apply(lambda x: RED if x > 0 else (GREEN if x < 0 else TEXT))
        st.markdown("<div class='section-title' style='margin-top:0;'>DAILY CALORIE DIFFERENCE</div>", unsafe_allow_html=True)
        bar_chart = alt.Chart(df.reset_index()).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X('Date:T', title='', axis=alt.Axis(domain=False, ticks=False, labelColor=MUTED, labelFont=CHART_FONT, labelFontSize=11, labelFontWeight='bold', labelPadding=8, labelExpr="upper(timeFormat(datum.value, '%a'))")),
            y=alt.Y('Net_Calories:Q', title='', axis=alt.Axis(domain=False, ticks=False, labelColor=MUTED, labelFont=CHART_FONT, labelFontSize=11, labelFontWeight='bold', labelPadding=8, grid=True, gridColor=TRACK)),
            color=alt.Color('Color:N', scale=None), tooltip=['Date', 'Net_Calories']
        ).properties(height=200, background='transparent').configure_view(strokeWidth=0)
        st.altair_chart(bar_chart, use_container_width=True)

        st.markdown("<div class='section-title'>AVERAGES</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PRO", f"{df['Protein'].mean():.0f}G")
        c2.metric("CARB", f"{df['Carbs'].mean():.0f}G")
        c3.metric("FAT", f"{df['Fats'].mean():.0f}G")
        c4.metric("SUG", f"{df['Sugars'].mean():.0f}G")

elif page == "MONTHLY OVERVIEW":
    page_title("MONTHLY OVERVIEW", PATHS["monthly"])
    df = get_dataframe(30)

    if df.empty: notice("NO DATA TO DISPLAY.")
    else:
        df['Color'] = df['Net_Calories'].apply(lambda x: RED if x > 0 else (GREEN if x < 0 else TEXT))
        st.markdown("<div class='section-title' style='margin-top:0;'>NET CALORIES (30 DAYS)</div>", unsafe_allow_html=True)
        scatter = alt.Chart(df.reset_index()).mark_circle(size=70, opacity=1.0).encode(
            x=alt.X('Date:T', title='', axis=alt.Axis(domain=False, ticks=False, labelColor=MUTED, labelFont=CHART_FONT, labelFontSize=11, labelFontWeight='bold', labelPadding=8, labelExpr="upper(timeFormat(datum.value, '%d %b'))")),
            y=alt.Y('Net_Calories:Q', title='', axis=alt.Axis(domain=False, ticks=False, labelColor=MUTED, labelFont=CHART_FONT, labelFontSize=11, labelFontWeight='bold', labelPadding=8, grid=True, gridColor=TRACK)),
            color=alt.Color('Color:N', scale=None), tooltip=['Date', 'Net_Calories']
        ).properties(height=220, background='transparent').configure_view(strokeWidth=0)
        st.altair_chart(scatter, use_container_width=True)

        st.metric("EST. WEIGHT CHANGE", f"{(df['Net_Calories'].sum() / 7700):+.2f} KG")

        st.markdown("<div class='section-title'>AI INSIGHTS</div>", unsafe_allow_html=True)
        if st.button("🌙 Gabriela's Day In Review", type="primary", key="habit_btn"):
            with st.spinner("ANALYZING..."):
                res = model.generate_content(f"Analyze 30-day nutrition: Avg Pro {df['Protein'].mean():.0f}g, Carbs {df['Carbs'].mean():.0f}g, Fats {df['Fats'].mean():.0f}g, Net Cal {df['Net_Calories'].sum()}. Give 3 brief, actionable habit recommendations.")
                st.markdown(res.text)

elif page == "GOALS":
    page_title("TARGET METRICS", PATHS["goals"])
    with st.form("goals_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        current_w = col1.number_input("CURRENT WEIGHT (KG)", value=float(data["goals"]["current_weight"]))
        desired_w = col2.number_input("DESIRED WEIGHT (KG)", value=float(data["goals"]["desired_weight"]))

        st.markdown("<div class='section-title'>MACRONUTRIENT TARGETS (G)</div>", unsafe_allow_html=True)
        c3, c4, c5 = st.columns(3)
        target_p = c3.number_input("PROTEIN", value=int(data["goals"]["target_protein"]))
        target_c = c4.number_input("CARBS", value=int(data["goals"]["target_carbs"]))
        target_f = c5.number_input("FATS", value=int(data["goals"]["target_fats"]))

        st.form_submit_button("UPDATE METRICS")
        data["goals"] = {"current_weight": current_w, "desired_weight": desired_w, "target_protein": target_p, "target_carbs": target_c, "target_fats": target_f}
        save_data(data)

elif page == "ASK":
    page_title("AI COACH", PATHS["ask"])

    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("ASK A QUESTION..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("..."):
                response = model.generate_content(f"Context: User weight is {data['goals']['current_weight']}kg. Speak concisely and professionally. " + prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
