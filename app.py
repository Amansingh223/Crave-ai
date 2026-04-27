import hashlib
import os
from datetime import date, datetime

import requests
import streamlit as st
from dotenv import load_dotenv

from chain import chat_with_chef, generate_recipes

load_dotenv()

# ─── Force-write .streamlit/config.toml (always overwrite, explicit UTF-8) ───
import pathlib, shutil

_config_dir  = pathlib.Path(".streamlit")
_config_file = _config_dir / "config.toml"

# Remove if it's a file masquerading as a folder or has wrong encoding
if _config_file.exists():
    try:
        _config_file.read_text(encoding="utf-8")  # test if readable
    except Exception:
        _config_file.unlink()  # delete corrupted file

if not _config_file.exists():
    _config_dir.mkdir(exist_ok=True)
    _lines = [
        "[theme]",
        'base = "dark"',
        'backgroundColor = "#0d0f12"',
        'secondaryBackgroundColor = "#141820"',
        'textColor = "#f0f2f7"',
        'primaryColor = "#f97316"',
        'font = "sans serif"',
    ]
    _config_file.write_text("\n".join(_lines) + "\n", encoding="utf-8")

st.set_page_config(
    page_title="Crave AI",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": "Crave AI helps you discover recipes from the ingredients you already have.",
        "Report a bug": "mailto:hello@eatcrave.in",
    },
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
        --bg: #0d0f12;
        --surface: #141820;
        --surface2: #1b2230;
        --surface3: #222c3a;
        --border: rgba(255,255,255,0.07);
        --border2: rgba(255,255,255,0.13);
        --text: #f0f2f7;
        --muted: #7a8799;
        --muted2: #4d5c6e;
        --orange: #f97316;
        --amber: #f59e0b;
        --orange-soft: rgba(249,115,22,0.12);
        --green: #22c55e;
        --green-soft: rgba(34,197,94,0.10);
        --r-sm: 10px;
        --r-md: 16px;
        --r-lg: 22px;
        --r-xl: 30px;
        --shadow: 0 20px 55px rgba(0,0,0,0.38);
    }

    /* ── App shell ── */
    .stApp {
        background:
            radial-gradient(circle at top left,  rgba(249,115,22,0.13) 0%, transparent 26%),
            radial-gradient(circle at top right, rgba(245,158,11,0.07) 0%, transparent 22%),
            var(--bg) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    .main .block-container {
        max-width: 1120px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    #MainMenu, footer, header, .stDeployButton { visibility: hidden; }

    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] { display: none !important; }

    /* ── Form inputs ── */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background: var(--surface2) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-sm) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif !important;
        min-height: 46px !important;
        transition: border-color 0.2s !important;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: rgba(249,115,22,0.4) !important;
        box-shadow: none !important;
    }

    .stTextArea textarea { min-height: 108px !important; }

    /* ── Buttons ── */
    .stButton > button,
    .stDownloadButton > button {
        border: none !important;
        border-radius: 999px !important;
        background: linear-gradient(135deg, var(--orange) 0%, var(--amber) 100%) !important;
        color: #0d0f12 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.93rem !important;
        padding: 0.75rem 1.4rem !important;
        box-shadow: 0 8px 28px rgba(249,115,22,0.28) !important;
        transition: transform 0.18s, box-shadow 0.18s !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 12px 36px rgba(249,115,22,0.38) !important;
    }

    /* ── Radio (difficulty selector) ── */
    div[data-testid="stRadio"] > div {
        gap: 0.4rem !important;
        flex-wrap: wrap !important;
    }

    div[data-testid="stRadio"] label {
        background: var(--surface2) !important;
        border: 1px solid var(--border) !important;
        border-radius: 999px !important;
        padding: 0.45rem 0.9rem !important;
        color: var(--muted) !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.82rem !important;
        cursor: pointer !important;
        transition: all 0.2s !important;
    }

    div[data-testid="stRadio"] label:has(input:checked) {
        background: var(--orange-soft) !important;
        border-color: rgba(249,115,22,0.35) !important;
        color: var(--orange) !important;
    }

    div[data-testid="stRadio"] input { display: none !important; }

    /* ── Multiselect chips ── */
    .stMultiSelect span[data-baseweb="tag"] {
        background: var(--orange-soft) !important;
        border: 1px solid rgba(249,115,22,0.25) !important;
        border-radius: 999px !important;
        color: var(--orange) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-lg) !important;
        padding: 0.35rem !important;
        gap: 0.2rem !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: var(--r-md) !important;
        color: var(--muted) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 0.6rem 0.9rem !important;
        transition: all 0.2s !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--surface3) !important;
        color: var(--text) !important;
    }

    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }
    .stTabs [data-baseweb="tab-border"]    { display: none !important; }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: var(--surface2) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        color: var(--muted) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
    }

    .streamlit-expanderContent {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 var(--r-md) var(--r-md) !important;
    }

    /* ── Chat messages ── */
    .stChatMessage {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
    }

    /* ── Info / success / error banners ── */
    .stAlert {
        background: var(--surface2) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--r-md) !important;
        color: var(--text) !important;
    }

    /* ── Checkbox ── */
    .stCheckbox label span { color: var(--text) !important; }

    /* ── Reusable layout primitives ── */
    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--orange-soft);
        border: 1px solid rgba(249,115,22,0.2);
        border-radius: 999px;
        padding: 0.3rem 0.75rem;
        color: var(--orange);
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 0.9rem;
    }

    .section-kicker {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--orange);
        margin-bottom: 0.3rem;
    }

    /* ── Hero ── */
    .hero-shell {
        background: linear-gradient(135deg, var(--surface) 0%, var(--surface2) 100%);
        border: 1px solid var(--border);
        border-radius: var(--r-xl);
        padding: 2.2rem 2.4rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }

    .hero-shell::before {
        content: '';
        position: absolute;
        top: -80px; right: -80px;
        width: 280px; height: 280px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(249,115,22,0.18) 0%, transparent 70%);
        pointer-events: none;
    }

    .hero-shell::after {
        content: '';
        position: absolute;
        bottom: -60px; left: 30%;
        width: 200px; height: 200px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 70%);
        pointer-events: none;
    }

    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: clamp(2rem, 5vw, 3.4rem);
        line-height: 1;
        letter-spacing: -0.03em;
        color: var(--text);
        margin: 0.6rem 0 0.75rem;
    }

    .hero-title em { color: var(--orange); font-style: normal; }

    .hero-copy {
        color: var(--muted);
        font-size: 0.93rem;
        line-height: 1.75;
        max-width: 520px;
    }

    /* ── Metric cards ── */
    .metrics-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.75rem;
        margin-top: 1.6rem;
    }

    .metric-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--border);
        border-radius: var(--r-md);
        padding: 0.9rem 1rem;
    }

    .metric-label {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted2);
        font-weight: 700;
        margin-bottom: 0.35rem;
    }

    .metric-val {
        font-family: 'Playfair Display', serif;
        font-size: 1.7rem;
        color: var(--text);
        line-height: 1;
    }

    .metric-val.accent { color: var(--orange); }

    .metric-sub {
        font-size: 0.74rem;
        color: var(--muted);
        margin-top: 0.3rem;
        line-height: 1.4;
    }

    /* ── Controls panel ── */
    .controls-panel {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-lg);
        padding: 1.6rem;
        margin-bottom: 1.5rem;
    }

    .panel-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.35rem;
        color: var(--text);
        margin-bottom: 0.25rem;
    }

    .panel-sub {
        font-size: 0.83rem;
        color: var(--muted);
        margin-bottom: 1.3rem;
        line-height: 1.65;
    }

    /* ── Recipe card ── */
    .recipe-shell {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-lg);
        overflow: hidden;
        margin-bottom: 1.1rem;
        transition: border-color 0.2s;
    }

    .recipe-shell:hover { border-color: var(--border2); }

    .recipe-img-wrap {
        position: relative;
        height: 190px;
        overflow: hidden;
        background: linear-gradient(135deg, var(--surface2), var(--surface3));
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.5rem;
    }

    .recipe-img {
        width: 100%; height: 100%;
        object-fit: cover;
        display: block;
    }

    .badge-time {
        position: absolute; top: 0.75rem; left: 0.75rem;
        background: rgba(13,15,18,0.85);
        border: 1px solid var(--border2);
        border-radius: 999px;
        color: var(--orange);
        font-size: 0.72rem; font-weight: 700;
        padding: 0.3rem 0.75rem;
    }

    .badge-diff {
        position: absolute; top: 0.75rem; right: 0.75rem;
        background: rgba(13,15,18,0.85);
        border: 1px solid var(--border2);
        border-radius: 999px;
        color: var(--text);
        font-size: 0.72rem; font-weight: 600;
        padding: 0.3rem 0.75rem;
    }

    .recipe-body { padding: 1.2rem; }

    .recipe-name {
        font-family: 'Playfair Display', serif;
        font-size: 1.3rem;
        color: var(--text);
        margin-bottom: 0.4rem;
    }

    .recipe-desc {
        font-size: 0.83rem;
        color: var(--muted);
        line-height: 1.65;
        margin-bottom: 0.85rem;
    }

    .chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.85rem; }

    .chip {
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 999px;
        color: var(--muted);
        font-size: 0.72rem; font-weight: 600;
        padding: 0.3rem 0.65rem;
    }

    .chip.green {
        background: var(--green-soft);
        border-color: rgba(34,197,94,0.2);
        color: var(--green);
    }

    /* ── Saved card ── */
    .saved-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-lg);
        padding: 1.1rem;
        margin-bottom: 0.75rem;
        height: 100%;
    }

    .saved-cuisine {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--orange);
        margin-bottom: 0.4rem;
    }

    .saved-name {
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        color: var(--text);
        margin-bottom: 0.4rem;
    }

    /* ── Meal plan ── */
    .plan-day {
        font-family: 'Playfair Display', serif;
        font-size: 1.15rem;
        color: var(--muted);
        margin: 1rem 0 0.6rem;
    }

    .plan-item {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-md);
        padding: 0.85rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--text);
    }

    /* ── Shopping ── */
    .shop-item {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-md);
        padding: 0.7rem 0.9rem;
        font-size: 0.87rem;
        color: var(--text);
        margin-bottom: 0.4rem;
    }

    /* ── Empty state ── */
    .empty-state {
        background: var(--surface);
        border: 1px dashed var(--border2);
        border-radius: var(--r-lg);
        padding: 2.5rem;
        text-align: center;
        color: var(--muted);
    }

    .empty-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }

    .empty-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.2rem;
        color: var(--text);
        margin-bottom: 0.5rem;
    }

    .empty-sub { font-size: 0.84rem; line-height: 1.65; }

    /* ── Auth ── */
    .auth-hero {
        background: linear-gradient(145deg, #131922 0%, #28180f 100%);
        border-radius: var(--r-xl);
        padding: 2.2rem;
        position: relative;
        overflow: hidden;
    }

    .auth-hero::after {
        content: '';
        position: absolute;
        right: -20px; top: -20px;
        width: 180px; height: 180px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.12), transparent 70%);
    }

    .auth-title {
        font-family: 'Playfair Display', serif;
        font-size: clamp(2rem, 4vw, 3.2rem);
        color: #fff7ee;
        line-height: 0.97;
        margin: 0.8rem 0 1rem;
        letter-spacing: -0.03em;
    }

    .auth-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-xl);
        padding: 1.8rem;
    }

    .auth-kicker {
        color: var(--orange);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 0.72rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* ── Info cards (about) ── */
    .info-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-lg);
        padding: 1.3rem;
        height: 100%;
    }

    /* ── Section headers ── */
    .section-title {
        font-family: 'Playfair Display', serif;
        font-size: clamp(1.6rem, 3vw, 2.2rem);
        color: var(--text);
        letter-spacing: -0.02em;
        margin-bottom: 0.4rem;
    }

    .section-copy {
        font-size: 0.85rem;
        color: var(--muted);
        line-height: 1.7;
        margin-bottom: 1.2rem;
    }

    /* ── Footer ── */
    .footer-note {
        text-align: center;
        color: var(--muted2);
        font-size: 0.82rem;
        margin-top: 2.5rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border);
    }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        .hero-shell { padding: 1.4rem 1.2rem; }
        .metrics-row { grid-template-columns: repeat(2, 1fr); }
        .main .block-container { padding-left: 1rem; padding-right: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Session state ─────────────────────────────────────────────────────────────
DEFAULTS = {
    "chat_history": [],
    "recipes": [],
    "saved_recipes": [],
    "logged_in": False,
    "username": "",
    "users_db": {},
    "meal_plan": {},
    "shopping_list": [],
    "checked_items": [],
    "auth_mode": "login",
    "filters": {
        "ingredients": "",
        "special": "",
        "diet": [],
        "cuisine": "Any cuisine",
        "time": "Any time",
        "difficulty": "Any",
    },
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

RECIPE_EMOJI = {"Indian": "🍛", "Italian": "🍝", "Asian": "🍜", "Mexican": "🌮",
                "Mediterranean": "🥗", "American": "🍔", "French": "🥐",
                "Middle Eastern": "🧆", "Japanese": "🍱", "Any cuisine": "🥘"}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_food_image(recipe_name: str) -> str:
    if UNSPLASH_KEY and UNSPLASH_KEY != "your_unsplash_access_key_here":
        try:
            query = "+".join(recipe_name.split()[:3])
            url = (
                f"https://api.unsplash.com/photos/random"
                f"?query={query}+food&orientation=landscape&client_id={UNSPLASH_KEY}"
            )
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json()["urls"]["regular"]
        except Exception:
            pass
    seed = abs(hash(recipe_name)) % 1000
    return f"https://source.unsplash.com/900x600/?{recipe_name.replace(' ', ',')},food&sig={seed}"


def render_section_header(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="section-kicker">{kicker}</div>
        <div class="section-title">{title}</div>
        <div class="section-copy">{copy}</div>
        """,
        unsafe_allow_html=True,
    )


def render_empty(icon: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-icon">{icon}</div>
            <div class="empty-title">{title}</div>
            <div class="empty-sub">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Auth page ────────────────────────────────────────────────────────────────
def auth_page() -> None:
    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.markdown(
            """
            <div class="auth-hero">
                <div class="eyebrow">🔥 Cook smarter</div>
                <h1 class="auth-title">Recipes from what you already have.</h1>
                <p style="color:rgba(255,247,238,0.82);line-height:1.8;max-width:520px;font-size:0.93rem;">
                    Crave AI turns random fridge ingredients into polished meal ideas,
                    guided cooking steps, nutrition insights, and practical chef advice.
                </p>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin-top:1.6rem;">
                    <div style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:0.9rem;">
                        <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#ffdba9;margin-bottom:0.4rem;">Recipe matches</div>
                        <div style="font-family:'Playfair Display',serif;font-size:1.4rem;color:#fff;">3 instant ideas</div>
                        <div style="font-size:0.76rem;color:rgba(255,247,238,0.7);margin-top:0.3rem;line-height:1.5;">Generated from your pantry</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:0.9rem;">
                        <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#ffdba9;margin-bottom:0.4rem;">Ask chef</div>
                        <div style="font-family:'Playfair Display',serif;font-size:1.4rem;color:#fff;">Smart guidance</div>
                        <div style="font-size:0.76rem;color:rgba(255,247,238,0.7);margin-top:0.3rem;line-height:1.5;">Substitutions & techniques</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:0.9rem;">
                        <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#ffdba9;margin-bottom:0.4rem;">Stay organized</div>
                        <div style="font-family:'Playfair Display',serif;font-size:1.4rem;color:#fff;">Plan the week</div>
                        <div style="font-size:0.76rem;color:rgba(255,247,238,0.7);margin-top:0.3rem;line-height:1.5;">Save meals & shop smarter</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        mode = st.session_state.auth_mode
        st.markdown(
            f"""
            <div class="auth-card">
                <div class="auth-kicker">{'Welcome back' if mode == 'login' else 'Create your account'}</div>
                <div class="section-title" style="font-size:1.9rem;">{'Sign in to Crave' if mode == 'login' else 'Join Crave AI'}</div>
                <div class="section-copy" style="margin-top:0.4rem;">{'Continue where you left off.' if mode == 'login' else 'Start cooking with your personal recipe assistant.'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if mode == "signup":
            st.text_input("Full name", placeholder="Aman Sharma", key="signup_name")
            st.text_input("Email", placeholder="aman@example.com", key="signup_email")

        username = st.text_input("Username", placeholder="aman123", key="auth_username")
        password = st.text_input("Password", placeholder="Enter password", type="password", key="auth_password")

        col_a, col_b = st.columns(2)
        with col_a:
            if mode == "login":
                if st.button("Sign in", use_container_width=True):
                    db = st.session_state.users_db
                    if username in db and db[username]["password"] == hash_pw(password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
            else:
                if st.button("Create account", use_container_width=True):
                    if not username or not password:
                        st.error("Username and password are required.")
                    elif username in st.session_state.users_db:
                        st.error("That username is already taken.")
                    else:
                        name = st.session_state.get("signup_name", "") or username
                        email = st.session_state.get("signup_email", "")
                        st.session_state.users_db[username] = {
                            "password": hash_pw(password),
                            "name": name,
                            "email": email,
                        }
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.rerun()

        with col_b:
            if st.button("Continue as guest", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.username = "guest"
                st.rerun()

        if mode == "login":
            st.caption("No account yet?")
            if st.button("Switch to signup →", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.rerun()
        else:
            st.caption("Already have an account?")
            if st.button("Switch to login →", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()

    st.markdown(
        '<div class="footer-note">Built for everyday home cooks: discover recipes, ask questions, save favorites, plan meals, and shop smarter.</div>',
        unsafe_allow_html=True,
    )


# ─── Hero + metrics bar ───────────────────────────────────────────────────────
def render_hero(display_name: str) -> None:
    planned = sum(len(v) for v in st.session_state.meal_plan.values())
    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="eyebrow">✦ Crave AI dashboard</div>
            <h1 class="hero-title">Cook with <em>confidence</em>,<br>not guesswork.</h1>
            <p class="hero-copy">
                Welcome back, {display_name}. Set your ingredients, explore recipes,
                ask the chef anything, and plan your whole week — all in one place.
            </p>
            <div class="metrics-row">
                <div class="metric-card">
                    <div class="metric-label">Recipes ready</div>
                    <div class="metric-val accent">{len(st.session_state.recipes)}</div>
                    <div class="metric-sub">Fresh ideas in Discover</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Saved dishes</div>
                    <div class="metric-val">{len(st.session_state.saved_recipes)}</div>
                    <div class="metric-sub">Your favorites</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Planned meals</div>
                    <div class="metric-val">{planned}</div>
                    <div class="metric-sub">This week</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Shopping items</div>
                    <div class="metric-val">{len(st.session_state.shopping_list)}</div>
                    <div class="metric-sub">On your list</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Controls panel ───────────────────────────────────────────────────────────
def controls_panel(display_name: str) -> bool:
    filters = st.session_state.filters

    st.markdown(
        f"""
        <div class="controls-panel">
            <div class="panel-title">Build your next meal, {display_name.split()[0]}</div>
            <div class="panel-sub">Tell Crave what you have and how you want to cook — three polished recipes come back in seconds.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🥄 Recipe controls — ingredients, diet, cuisine, time, difficulty", expanded=True):
        top_left, top_right = st.columns([1.6, 1], gap="large")

        with top_left:
            filters["ingredients"] = st.text_area(
                "Available ingredients",
                value=filters["ingredients"],
                placeholder="chicken, garlic, yogurt, tomato, spinach...",
            )

        with top_right:
            filters["special"] = st.text_input(
                "Special request",
                value=filters["special"],
                placeholder="high protein, weeknight, spicy",
            )
            filters["cuisine"] = st.selectbox(
                "Cuisine",
                ["Any cuisine", "Indian", "Italian", "Asian", "Mexican",
                 "Mediterranean", "American", "French", "Middle Eastern", "Japanese"],
                index=["Any cuisine", "Indian", "Italian", "Asian", "Mexican",
                       "Mediterranean", "American", "French", "Middle Eastern", "Japanese"].index(filters["cuisine"]),
            )

        row_a, row_b, row_c = st.columns(3, gap="large")

        with row_a:
            filters["diet"] = st.multiselect(
                "Dietary preferences",
                ["Vegetarian", "Vegan", "Gluten-Free", "Keto",
                 "Dairy-Free", "Low-Carb", "High-Protein", "Paleo"],
                default=filters["diet"],
            )

        with row_b:
            filters["time"] = st.selectbox(
                "Cooking time",
                ["Any time", "Under 15 mins", "15–30 mins", "30–60 mins", "Over 1 hour"],
                index=["Any time", "Under 15 mins", "15–30 mins", "30–60 mins", "Over 1 hour"].index(filters["time"]),
            )

        with row_c:
            filters["difficulty"] = st.radio(
                "Difficulty",
                ["Any", "Easy", "Medium", "Hard"],
                index=["Any", "Easy", "Medium", "Hard"].index(filters["difficulty"]),
                horizontal=True,
            )

        gen_col, out_col = st.columns([4, 1])
        with gen_col:
            clicked = st.button("🍳 Generate recipes", use_container_width=True)
        with out_col:
            if st.button("Sign out", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.auth_mode = "login"
                st.rerun()

    return clicked


# ─── Recipe generation ────────────────────────────────────────────────────────
def handle_generate() -> None:
    f = st.session_state.filters
    if not f["ingredients"].strip():
        st.warning("Add at least a few ingredients before generating recipes.")
        return

    with st.spinner("Generating recipe ideas with Crave AI..."):
        try:
            recipes = generate_recipes(
                ingredients=f["ingredients"],
                diet=f["diet"],
                cuisine="" if f["cuisine"] == "Any cuisine" else f["cuisine"],
                time="" if f["time"] == "Any time" else f["time"],
                difficulty="" if f["difficulty"] == "Any" else f["difficulty"],
                special=f["special"],
            )
            for r in recipes:
                r["img_url"] = get_food_image(r["name"])
            st.session_state.recipes = recipes
            st.success("Fresh recipe ideas are ready — check the Discover tab.")
        except Exception as exc:
            st.error(f"Recipe generation failed: {exc}")


# ─── Recipe card ──────────────────────────────────────────────────────────────
def recipe_card(recipe: dict, idx: int) -> None:
    cuisine = recipe.get("cuisine", "Mixed")
    emoji = RECIPE_EMOJI.get(cuisine, "🥘")
    img = recipe.get("img_url", "")
    is_saved = any(s["name"] == recipe["name"] for s in st.session_state.saved_recipes)

    img_tag = (
        f'<img class="recipe-img" src="{img}" alt="{recipe["name"]}" '
        f'onerror="this.style.display=\'none\'">'
        if img else ""
    )

    st.markdown(
        f"""
        <div class="recipe-shell">
            <div class="recipe-img-wrap">
                {img_tag if img else emoji}
                <span class="badge-time">{recipe.get('time','Quick')}</span>
                <span class="badge-diff">{recipe.get('difficulty','Any')}</span>
            </div>
            <div class="recipe-body">
                <div class="recipe-name">{recipe['name']}</div>
                <div class="recipe-desc">{recipe.get('description','')}</div>
                <div class="chip-row">
                    <span class="chip green">{cuisine}</span>
                    <span class="chip">{recipe.get('calories','~')}</span>
                    <span class="chip">Protein {recipe.get('protein','--')}</span>
                    <span class="chip">Carbs {recipe.get('carbs','--')}</span>
                    <span class="chip">Fat {recipe.get('fat','--')}</span>
                    <span class="chip">{recipe.get('servings','2 servings')}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    view_col, save_col, plan_col = st.columns([3.5, 1.4, 1.5])

    with view_col:
        with st.expander("View ingredients, method & chef tip"):
            st.markdown("**Ingredients**")
            for ing in recipe.get("ingredients", []):
                st.markdown(f"- {ing}")
            st.markdown("**Method**")
            for n, step in enumerate(recipe.get("steps", []), 1):
                st.markdown(f"{n}. {step}")
            if recipe.get("tip"):
                st.info(f"💡 Chef tip: {recipe['tip']}")

    with save_col:
        label = "✓ Saved" if is_saved else "Save"
        if st.button(label, key=f"save_{idx}_{recipe['name']}", use_container_width=True):
            if is_saved:
                st.session_state.saved_recipes = [
                    s for s in st.session_state.saved_recipes if s["name"] != recipe["name"]
                ]
            else:
                st.session_state.saved_recipes.append(recipe)
            st.rerun()

    with plan_col:
        if st.button("Add to plan", key=f"plan_{idx}_{recipe['name']}", use_container_width=True):
            today = str(date.today())
            st.session_state.meal_plan.setdefault(today, [])
            if recipe["name"] not in st.session_state.meal_plan[today]:
                st.session_state.meal_plan[today].append(recipe["name"])
                for ing in recipe.get("ingredients", []):
                    if ing not in st.session_state.shopping_list:
                        st.session_state.shopping_list.append(ing)
                st.success("Added to meal plan.")
            else:
                st.info("Already in today's meal plan.")


# ─── Tab: Discover ────────────────────────────────────────────────────────────
def tab_discover() -> None:
    render_section_header(
        "Recipe discovery",
        "Find the best thing to cook right now.",
        "Crave AI looks at your ingredients, diet, time, and difficulty to propose three polished recipe ideas.",
    )

    if not st.session_state.recipes:
        render_empty("🥗", "No recipes generated yet",
                     "Open the recipe controls above, describe what's in your kitchen, and click Generate recipes.")
    else:
        for i, recipe in enumerate(st.session_state.recipes):
            recipe_card(recipe, i)


# ─── Tab: Ask Chef ────────────────────────────────────────────────────────────
def tab_chef() -> None:
    render_section_header(
        "Chef assistant",
        "Ask follow-up questions like a real cooking conversation.",
        "Substitutions, troubleshooting, pairings, nutrition, or adapting recipes — the chef is here.",
    )

    sugg_cols = st.columns(3)
    suggestions = [
        "What can I use instead of cream?",
        "Make this recipe high protein",
        "How do I fix bland curry?",
    ]
    for col, sug in zip(sugg_cols, suggestions):
        with col:
            if st.button(sug, key=f"sug_{sug}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": sug})
                with st.spinner("Chef is thinking..."):
                    reply = chat_with_chef(st.session_state.chat_history[:-1], sug)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

    if not st.session_state.chat_history:
        st.markdown(
            """
            <div class="empty-state" style="margin-bottom:1rem;">
                <div class="empty-icon">👨‍🍳</div>
                <div class="empty-title">Start with any cooking question</div>
                <div class="empty-sub">Example: "I have paneer, spinach, and onions. What can I cook in 20 minutes?"</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask Crave AI anything about cooking..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("Chef is thinking..."):
            reply = chat_with_chef(st.session_state.chat_history[:-1], user_input)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("Clear chat", use_container_width=False):
            st.session_state.chat_history = []
            st.rerun()


# ─── Tab: Saved ───────────────────────────────────────────────────────────────
def tab_saved() -> None:
    render_section_header(
        "Saved recipes",
        "Keep your best discoveries handy.",
        "Anything you save from Discover will live here for quick access.",
    )

    if not st.session_state.saved_recipes:
        render_empty("🔖", "Nothing saved yet", "Save a recipe from the Discover tab and it will appear here.")
        return

    cols = st.columns(2)
    for i, recipe in enumerate(st.session_state.saved_recipes):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div class="saved-card">
                    <div class="saved-cuisine">{recipe.get('cuisine','Mixed cuisine')}</div>
                    <div class="saved-name">{recipe['name']}</div>
                    <div class="section-copy" style="margin-bottom:0.75rem;">{recipe.get('description','')}</div>
                    <div class="chip-row">
                        <span class="chip">{recipe.get('time','Quick')}</span>
                        <span class="chip">{recipe.get('difficulty','Any')}</span>
                        <span class="chip">{recipe.get('calories','~')}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Remove", key=f"rm_saved_{i}", use_container_width=True):
                st.session_state.saved_recipes.pop(i)
                st.rerun()


# ─── Tab: Meal Plan ───────────────────────────────────────────────────────────
def tab_meal_plan() -> None:
    render_section_header(
        "Meal planning",
        "Turn favorites into a simple weekly plan.",
        "When you add a recipe, its ingredients flow into your shopping list automatically.",
    )

    if not st.session_state.meal_plan:
        render_empty("📅", "No planned meals yet", "Use 'Add to plan' on any recipe to build your schedule.")
        return

    for day, meals in sorted(st.session_state.meal_plan.items()):
        try:
            pretty = datetime.strptime(day, "%Y-%m-%d").strftime("%A, %d %b %Y")
        except Exception:
            pretty = day

        st.markdown(f'<div class="plan-day">{pretty}</div>', unsafe_allow_html=True)

        for meal in meals:
            left, right = st.columns([6, 1])
            with left:
                st.markdown(f'<div class="plan-item">{meal}</div>', unsafe_allow_html=True)
            with right:
                if st.button("Remove", key=f"rm_plan_{day}_{meal}", use_container_width=True):
                    st.session_state.meal_plan[day].remove(meal)
                    if not st.session_state.meal_plan[day]:
                        del st.session_state.meal_plan[day]
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Clear all meals", use_container_width=True):
        st.session_state.meal_plan = {}
        st.rerun()


# ─── Tab: Shopping ────────────────────────────────────────────────────────────
def tab_shopping() -> None:
    render_section_header(
        "Shopping list",
        "Stay organized while you cook through the week.",
        "Auto-filled from planned meals. Add items manually and check them off as you shop.",
    )

    add_col, btn_col = st.columns([5, 1])
    with add_col:
        new_item = st.text_input("Add ingredient", placeholder="2 cups basmati rice", label_visibility="collapsed")
    with btn_col:
        if st.button("Add", use_container_width=True):
            item = new_item.strip()
            if item and item not in st.session_state.shopping_list:
                st.session_state.shopping_list.append(item)
                st.rerun()

    if not st.session_state.shopping_list:
        render_empty("🛒", "Shopping list is empty", "Plan a recipe or add ingredients manually.")
        return

    checked = set(st.session_state.checked_items)

    for item in list(st.session_state.shopping_list):
        chk_col, name_col, del_col = st.columns([0.5, 6, 1])
        with chk_col:
            ticked = st.checkbox("", value=item in checked, key=f"chk_{item}")
            if ticked:
                checked.add(item)
            else:
                checked.discard(item)
        with name_col:
            style = "text-decoration:line-through;color:var(--muted2);" if item in checked else ""
            st.markdown(f'<div class="shop-item" style="{style}">{item}</div>', unsafe_allow_html=True)
        with del_col:
            if st.button("✕", key=f"del_{item}", use_container_width=True):
                st.session_state.shopping_list.remove(item)
                checked.discard(item)
                st.session_state.checked_items = list(checked)
                st.rerun()

    st.session_state.checked_items = list(checked)

    clear_col, dl_col = st.columns(2)
    with clear_col:
        if st.button("Clear bought items", use_container_width=True):
            st.session_state.shopping_list = [i for i in st.session_state.shopping_list if i not in checked]
            st.session_state.checked_items = []
            st.rerun()
    with dl_col:
        txt = "\n".join(f"- {i}" for i in st.session_state.shopping_list)
        st.download_button("Download list", txt, file_name="crave-shopping-list.txt",
                           mime="text/plain", use_container_width=True)


# ─── Tab: About ───────────────────────────────────────────────────────────────
def tab_about() -> None:
    render_section_header(
        "About Crave AI",
        "A calmer, smarter recipe assistant for everyday kitchens.",
        "Crave focuses on practical recipe discovery, conversation, planning, and shopping.",
    )

    left, right = st.columns([1.3, 0.9], gap="large")

    with left:
        st.markdown(
            """
            <div class="info-card">
                <div class="section-kicker">Our story</div>
                <div class="section-title" style="font-size:1.8rem;margin-top:0.4rem;">
                    Built for the "what can I cook today?" moment.
                </div>
                <div class="section-copy" style="margin-top:0.75rem;">
                    Crave AI is designed for real kitchens, not idealized ones. You start with the
                    ingredients you already have, set a few preferences, and get recipes that feel
                    useful, attractive, and easy to act on. Less waste, less friction, better meals
                    on busy days.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="info-card">
                <div class="section-kicker">Tech stack</div>
                <div class="chip-row" style="margin-top:0.9rem;">
                    <span class="chip">Python</span>
                    <span class="chip">Streamlit</span>
                    <span class="chip">LangChain</span>
                    <span class="chip">Groq</span>
                    <span class="chip">Llama 3.3</span>
                </div>
                <div class="section-copy" style="margin-top:1rem;">
                    Fast recipe generation, chef chat, and a responsive UI designed for
                    both desktop and mobile layouts.
                </div>
                <div style="margin-top:1rem;padding-top:0.9rem;border-top:1px solid var(--border);">
                    <div class="section-kicker">Contact</div>
                    <div class="section-copy" style="margin-top:0.3rem;">hello@eatcrave.in</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ─── Main ─────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    auth_page()
    st.stop()

user_info = st.session_state.users_db.get(st.session_state.username, {})
display_name = user_info.get("name", st.session_state.username or "Guest")

render_hero(display_name.split()[0])

gen_clicked = controls_panel(display_name)
if gen_clicked:
    handle_generate()

tabs = st.tabs(["🍽 Discover", "👨‍🍳 Ask Chef", "🔖 Saved", "📅 Meal Plan", "🛒 Shopping", "ℹ About"])

with tabs[0]:
    tab_discover()

with tabs[1]:
    tab_chef()

with tabs[2]:
    tab_saved()

with tabs[3]:
    tab_meal_plan()

with tabs[4]:
    tab_shopping()

with tabs[5]:
    tab_about()

st.markdown(
    '<div class="footer-note">Crave AI • recipe discovery, chef chat, meal planning, and shopping in one responsive app.</div>',
    unsafe_allow_html=True,
)