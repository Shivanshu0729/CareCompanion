APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap');

:root {
  --navy: #12263A;
  --ink: #1C3348;
  --teal: #1F6F8B;
  --teal-soft: #D7E8EE;
  --paper: #F3F6FB;
  --card: #FFFFFF;
  --line: #D9E2EC;
  --muted: #5B6B7C;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--paper);
  color: var(--navy);
  font-family: Manrope, sans-serif;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }

section[data-testid="stSidebar"] {
  background: #102233;
  border-right: 1px solid #163247;
}
section[data-testid="stSidebar"] * {
  color: #E8F1F6 !important;
}
section[data-testid="stSidebar"] .stButton > button {
  background: #17364A;
  border: 1px solid #2A5166;
  color: #F4FBFF !important;
  border-radius: 12px;
  width: 100%;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: #1F6F8B;
  border-color: #1F6F8B;
}

section[data-testid="stSidebar"] [data-testid="column"]:last-child .stButton > button {
  min-width: 32px !important;
  width: 32px !important;
  min-height: 34px !important;
  height: 34px !important;
  padding: 0 !important;
  background: #17364A !important;
  border: 1px solid #2A5166 !important;
  color: #FFFFFF !important;
  font-size: 1.15rem !important;
  line-height: 1 !important;
}

section[data-testid="stSidebar"] [data-testid="column"]:last-child .stButton > button:hover {
  background: #1F6F8B !important;
  border-color: #6EAFC3 !important;
}

section[data-testid="stSidebar"] [data-testid="stPopover"] > div[role="dialog"] {
  background: #102233 !important;
  border: 1px solid #2A5166 !important;
  border-radius: 10px !important;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35) !important;
  min-width: 150px !important;
  max-width: 190px !important;
  padding: 0.35rem !important;
}

section[data-testid="stSidebar"] [data-testid="stPopover"] [data-testid="stPopoverButton"] {
  min-width: 32px !important;
  width: 32px !important;
  height: 34px !important;
  padding: 0 !important;
  font-size: 1.15rem !important;
  background: #17364A !important;
  border: 0 !important;
  color: #FFFFFF !important;
}

section[data-testid="stSidebar"] [data-testid="stPopover"] [data-testid="stPopoverButton"]:hover {
  background: #1F6F8B !important;
}

section[data-testid="stSidebar"] [data-testid="stPopover"] .stButton > button {
  background: transparent !important;
  border: 0 !important;
  border-radius: 7px !important;
  color: #E8F1F6 !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  text-align: left !important;
}

section[data-testid="stSidebar"] [data-testid="stPopover"] .stButton > button:hover {
  background: #17364A !important;
  color: #FFFFFF !important;
}

.thread-menu-separator {
  border-top: 1px solid #2A5166;
  margin: 0.2rem 0;
}

.block-container {
  padding-top: 1.6rem;
  max-width: 1180px;
}

.cc-logo {
  font-family: "Source Serif 4", serif;
  font-size: 1.35rem;
  letter-spacing: 0.01em;
  margin-bottom: 0.2rem;
}
.cc-mark {
  display: inline-flex;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: #1F6F8B;
  color: white;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  margin-right: 8px;
}

.cc-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 1.2rem 1.3rem;
  box-shadow: 0 10px 30px rgba(18, 38, 58, 0.05);
}

.page-subtitle {
  color: var(--muted);
  font-size: 1rem;
  margin: -0.5rem 0 1.5rem;
  max-width: 700px;
}

.sidebar-label {
  color: #9EB4C2;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin: 1.25rem 0 0.45rem;
  text-transform: uppercase;
}

.sidebar-divider {
  border-top: 1px solid #244154;
  margin: 1.2rem 0;
}

.sidebar-account {
  align-items: center;
  color: #B9CAD3;
  display: flex;
  font-size: 0.78rem;
  gap: 0.45rem;
  margin: 1rem 0 0.65rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dot {
  background: #6EAFC3;
  border-radius: 50%;
  display: inline-block;
  height: 8px;
  min-width: 8px;
  width: 8px;
}

.metric-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0.85rem 1rem 0.5rem;
}

.cc-kicker {
  color: var(--teal);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1, h2, h3 {
  font-family: "Source Serif 4", serif;
  color: var(--navy);
}

.stChatMessage {
  background: white;
  border: 1px solid var(--line);
  border-radius: 16px;
}

div[data-testid="stChatMessageAvatar"],
div[data-testid="stChatMessageAvatarUser"],
div[data-testid="stChatMessageAvatarAssistant"],
div[data-testid="stSpinner"] svg {
  display: none !important;
}

div[data-testid="stChatMessage"] > div:first-child {
  display: none !important;
}

div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
  background: #EAF3F7;
}

.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
  border-radius: 12px !important;
}

.stButton > button {
  border-radius: 12px;
  background: var(--teal);
  color: white;
  border: 0;
  font-weight: 600;
}

.metric-label { color: var(--muted); font-size: 0.82rem; }
.missing-pill {
  display: inline-block;
  background: #F4E8D8;
  color: #7A4E16;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.75rem;
}
.source-pill {
  display: inline-block;
  background: var(--teal-soft);
  color: var(--teal);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: 600;
}
</style>
"""


def inject_styles(st) -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
