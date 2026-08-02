"""Mahabharata / old-India visual theme for the Streamlit shell.

Direction: midnight indigo field, burnished gold, vermillion seals,
Devanagari + epic Latin display type. Not a purple SaaS gradient, not
cream-and-terracotta template AI.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

_ASSETS = Path(__file__).resolve().parent / "assets"


@lru_cache(maxsize=1)
def _wheel_data_uri() -> str:
    # Prefer clean reconstructed SVG; then PNG; then jpg.
    for name, mime in (
        ("gold_chakra.svg", "image/svg+xml"),
        ("konark_wheel.png", "image/png"),
        ("konark_wheel.jpg", "image/jpeg"),
    ):
        path = _ASSETS / name
        if path.exists():
            raw = path.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
            return f"data:{mime};base64,{b64}"
    raise FileNotFoundError("No wheel asset found in sentinelflow/ui/assets/")


THEME_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700&family=Cinzel:wght@400;600;700&family=Tiro+Devanagari+Sanskrit:ital@0;1&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">

<style>
:root {
  --sf-ink: #070b14;
  --sf-ink-2: #10182a;
  --sf-panel: rgba(16, 24, 42, 0.72);
  --sf-gold: #d4af37;
  --sf-gold-soft: #e8c978;
  --sf-gold-dim: #8a7020;
  --sf-vermillion: #c23b22;
  --sf-vermillion-deep: #8e2414;
  --sf-ivory: #f2e6c9;
  --sf-ivory-dim: #cbb991;
  --sf-sage: #6f8f6a;
  --sf-line: rgba(212, 175, 55, 0.35);
  --sf-shadow: 0 0 80px rgba(212, 175, 55, 0.08);
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--sf-ink) !important;
  color: var(--sf-ivory) !important;
  font-family: "Source Serif 4", Georgia, serif !important;
}

/* Atmospheric field: night sky + faint yantra lattice */
[data-testid="stAppViewContainer"] {
  background-color: var(--sf-ink) !important;
  background-image:
    radial-gradient(ellipse 90% 55% at 50% -10%, rgba(194, 59, 34, 0.18), transparent 55%),
    radial-gradient(ellipse 70% 45% at 80% 100%, rgba(212, 175, 55, 0.10), transparent 50%),
    radial-gradient(circle at 50% 40%, rgba(16, 24, 42, 0.2), transparent 60%),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 47px,
      rgba(212, 175, 55, 0.035) 48px
    ),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 47px,
      rgba(212, 175, 55, 0.035) 48px
    ),
    radial-gradient(circle at 50% 50%, transparent 28%, rgba(212, 175, 55, 0.04) 29%, transparent 30%),
    linear-gradient(180deg, #070b14 0%, #0c1424 45%, #070b14 100%) !important;
  background-attachment: fixed !important;
}

[data-testid="stHeader"] {
  background: transparent !important;
}
[data-testid="stToolbar"] { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

.block-container {
  max-width: 980px !important;
  padding-top: 1.2rem !important;
  padding-bottom: 4rem !important;
  position: relative;
  z-index: 1;
}

/* ——— Hero brand ——— */
.sf-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 2.4rem 1rem 1.6rem;
  position: relative;
  animation: sf-rise 1.1s ease-out both;
  width: 100%;
  box-sizing: border-box;
}
.sf-hero::before,
.sf-hero::after {
  content: "";
  display: block;
  height: 1px;
  max-width: 420px;
  margin: 0 auto 1.4rem;
  background: linear-gradient(90deg, transparent, var(--sf-gold), transparent);
}
.sf-hero::after { margin: 1.4rem auto 0; }

.sf-sanskrit {
  font-family: "Tiro Devanagari Sanskrit", "Noto Serif Devanagari", serif;
  font-size: 1.35rem;
  letter-spacing: 0.18em;
  color: var(--sf-gold-soft);
  margin: 0 0 0.55rem;
  text-shadow: 0 0 24px rgba(212, 175, 55, 0.25);
}
.sf-brand {
  font-family: "Cinzel Decorative", "Cinzel", serif;
  font-weight: 700;
  font-size: clamp(2.4rem, 6vw, 3.6rem);
  line-height: 1.05;
  margin: 0;
  background: linear-gradient(180deg, #f7e7a4 0%, var(--sf-gold) 45%, #8a7020 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  letter-spacing: 0.04em;
  animation: sf-shimmer 6s ease-in-out infinite;
}
.sf-tagline {
  font-family: "Cinzel", serif;
  font-size: 0.95rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--sf-ivory-dim);
  margin: 0.85rem 0 0;
}
.sf-epigraph {
  font-family: "Tiro Devanagari Sanskrit", serif;
  font-style: italic;
  color: var(--sf-ivory-dim);
  font-size: 1.05rem;
  margin: 0.9rem auto 0 !important;
  max-width: 42rem;
  width: 100%;
  line-height: 1.55;
  text-align: center !important;
  display: block;
  align-self: center;
}

/* ——— Section titles ——— */
.sf-section {
  margin: 2.2rem 0 0.9rem;
  text-align: center;
  animation: sf-rise 0.9s ease-out both;
}
.sf-section h2 {
  font-family: "Cinzel", serif;
  font-weight: 600;
  font-size: 1.35rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--sf-gold);
  margin: 0;
}
.sf-section p {
  color: var(--sf-ivory-dim);
  margin: 0.45rem 0 0;
  font-size: 1.02rem;
}

/* Manuscript panel */
.sf-panel {
  border: 1px solid var(--sf-line);
  background: var(--sf-panel);
  box-shadow: var(--sf-shadow), inset 0 0 0 1px rgba(212, 175, 55, 0.06);
  padding: 1.25rem 1.4rem;
  position: relative;
  margin: 0.6rem 0 1.2rem;
  animation: sf-rise 0.85s ease-out both;
}
.sf-panel::before,
.sf-panel::after {
  content: "✦";
  position: absolute;
  color: var(--sf-gold-dim);
  font-size: 0.7rem;
}
.sf-panel::before { top: 0.35rem; left: 0.45rem; }
.sf-panel::after { bottom: 0.35rem; right: 0.45rem; }

.sf-path {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.45rem;
  margin: 1rem 0 0.2rem;
}
.sf-step {
  font-family: "Cinzel", serif;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--sf-ivory-dim);
  border: 1px solid rgba(212, 175, 55, 0.25);
  padding: 0.45rem 0.7rem;
  min-width: 5.5rem;
  text-align: center;
  transition: color 0.35s, border-color 0.35s, background 0.35s, box-shadow 0.35s;
}
.sf-step.is-done {
  color: var(--sf-gold);
  border-color: var(--sf-gold);
  background: rgba(212, 175, 55, 0.08);
}
.sf-step.is-active {
  color: var(--sf-ink);
  background: linear-gradient(180deg, var(--sf-gold-soft), var(--sf-gold));
  border-color: var(--sf-gold);
  box-shadow: 0 0 22px rgba(212, 175, 55, 0.35);
  animation: sf-pulse 1.6s ease-in-out infinite;
}
.sf-step.is-fail {
  color: #ffd7cf;
  border-color: var(--sf-vermillion);
  background: rgba(194, 59, 34, 0.18);
}

.sf-seal {
  display: inline-block;
  font-family: "Cinzel", serif;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-size: 0.75rem;
  padding: 0.35rem 0.8rem;
  border: 1px solid var(--sf-gold);
  color: var(--sf-gold);
}
.sf-seal.vermillion {
  border-color: var(--sf-vermillion);
  color: #ffcfc4;
  background: rgba(194, 59, 34, 0.15);
}
.sf-seal.sage {
  border-color: var(--sf-sage);
  color: #cfe3cc;
  background: rgba(111, 143, 106, 0.15);
}

.sf-claim {
  border-left: 2px solid var(--sf-gold-dim);
  padding: 0.35rem 0 0.35rem 0.9rem;
  margin: 0.55rem 0;
  color: var(--sf-ivory);
}
.sf-cite {
  font-family: "Cinzel", serif;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  color: var(--sf-gold-soft);
}

.sf-footer {
  text-align: center;
  margin-top: 2.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--sf-line);
  font-family: "Cinzel", serif;
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--sf-gold-dim);
}

/* Streamlit widget restyle */
label, .stMarkdown, .stText, p, span, div {
  color: var(--sf-ivory);
}
[data-testid="stWidgetLabel"] p {
  font-family: "Cinzel", serif !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.72rem !important;
  color: var(--sf-ivory-dim) !important;
}
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
  background: rgba(7, 11, 20, 0.85) !important;
  color: var(--sf-ivory) !important;
  border: 1px solid var(--sf-line) !important;
  border-radius: 0 !important;
}
[data-testid="stFileUploader"] section {
  background: rgba(7, 11, 20, 0.55) !important;
  border: 1px dashed var(--sf-gold-dim) !important;
  border-radius: 0 !important;
}
[data-testid="stFileUploader"] section:hover {
  border-color: var(--sf-gold) !important;
  box-shadow: 0 0 28px rgba(212, 175, 55, 0.12);
}
.stButton > button {
  font-family: "Cinzel", serif !important;
  letter-spacing: 0.14em !important;
  text-transform: uppercase !important;
  border-radius: 0 !important;
  border: 1px solid var(--sf-gold) !important;
  background: linear-gradient(180deg, rgba(212,175,55,0.22), rgba(138,112,32,0.35)) !important;
  color: var(--sf-ivory) !important;
  transition:
    transform 0.18s cubic-bezier(0.34, 1.4, 0.64, 1),
    box-shadow 0.18s ease,
    background 0.18s ease,
    filter 0.18s ease !important;
  position: relative;
  z-index: 1;
}
.stButton > button:hover:not(:disabled) {
  transform: translateY(-3px) scale(1.055) !important;
  box-shadow:
    0 0 0 1px rgba(232, 201, 120, 0.55),
    0 10px 28px rgba(212, 175, 55, 0.35),
    0 0 36px rgba(212, 175, 55, 0.22) !important;
  background: linear-gradient(180deg, rgba(245, 220, 140, 0.5), rgba(212, 175, 55, 0.55)) !important;
  color: #fff8e0 !important;
  filter: brightness(1.08);
  z-index: 3;
}
.stButton > button:active:not(:disabled) {
  transform: translateY(-1px) scale(1.02) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(180deg, #e8c978, #d4af37 55%, #8a7020) !important;
  color: #14100a !important;
  border-color: var(--sf-gold-soft) !important;
  font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover:not(:disabled) {
  background: linear-gradient(180deg, #fff0b8, #e8c978 50%, #d4af37) !important;
  color: #0c0a06 !important;
  box-shadow:
    0 0 0 1px #f7e7a4,
    0 12px 32px rgba(232, 201, 120, 0.45),
    0 0 48px rgba(212, 175, 55, 0.3) !important;
}
@media (prefers-reduced-motion: reduce) {
  .stButton > button,
  .stButton > button:hover:not(:disabled) {
    transform: none !important;
    transition: background 0.15s ease, box-shadow 0.15s ease !important;
  }
}

/* Sample-case chips */
.sf-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  justify-content: center;
  margin: 0.4rem 0 1rem;
}
.sf-chip-hint {
  text-align: center;
  font-family: "Cinzel", serif;
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--sf-gold-dim);
  margin: 0.2rem 0 0.55rem;
}

/* Verdict banner */
.sf-verdict {
  text-align: center;
  padding: 1.4rem 1.2rem 1.2rem;
  margin: 0.6rem 0 1.1rem;
  border: 1px solid var(--sf-line);
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, rgba(212, 175, 55, 0.14), transparent 60%),
    rgba(16, 24, 42, 0.85);
  box-shadow: var(--sf-shadow);
  animation: sf-rise 0.7s ease-out both;
}
.sf-verdict .sf-v-label {
  font-family: "Cinzel", serif;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  font-size: 0.72rem;
  color: var(--sf-gold-soft);
  margin: 0 0 0.55rem;
}
.sf-verdict .sf-v-class {
  font-family: "Cinzel Decorative", "Cinzel", serif;
  font-size: clamp(1.4rem, 3.5vw, 2rem);
  color: var(--sf-gold);
  margin: 0.35rem 0;
  letter-spacing: 0.04em;
}
.sf-verdict .sf-v-meta {
  font-family: "Cinzel", serif;
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--sf-ivory-dim);
  margin: 0.35rem 0 0.7rem;
}
.sf-verdict .sf-v-summary {
  color: var(--sf-ivory);
  line-height: 1.55;
  margin: 0 auto;
  max-width: 36rem;
  font-size: 1.02rem;
}
.sf-loading {
  text-align: center;
  padding: 0.6rem 0 0.2rem;
  font-family: "Cinzel", serif;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-size: 0.78rem;
  color: var(--sf-gold-soft);
  animation: sf-pulse 1.4s ease-in-out infinite;
}
div[data-testid="stCheckbox"] label p {
  text-transform: none !important;
  letter-spacing: 0.02em !important;
  font-family: "Source Serif 4", serif !important;
  color: var(--sf-ivory-dim) !important;
}
.stAlert {
  border-radius: 0 !important;
  border: 1px solid var(--sf-line) !important;
  background: rgba(16, 24, 42, 0.9) !important;
}
[data-testid="stExpander"] {
  border: 1px solid var(--sf-line) !important;
  background: rgba(7, 11, 20, 0.55) !important;
  border-radius: 0 !important;
}
[data-testid="stExpander"] summary {
  font-family: "Cinzel", serif !important;
  letter-spacing: 0.08em;
  color: var(--sf-gold-soft) !important;
}
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: "Cinzel", serif !important;
  color: var(--sf-gold) !important;
}
.stMarkdown code {
  background: rgba(212, 175, 55, 0.1) !important;
  color: var(--sf-gold-soft) !important;
  border: 1px solid rgba(212, 175, 55, 0.2);
}
.stMarkdown pre {
  background: rgba(7, 11, 20, 0.85) !important;
  border: 1px solid var(--sf-line) !important;
  border-radius: 0 !important;
}
hr {
  border: none !important;
  border-top: 1px solid var(--sf-line) !important;
}

/* Konark chakra — fixed bottom-left, slow sacred rotation.
   Background image is injected at runtime (data URI) so Streamlit
   sanitizers cannot strip an <img> tag. */
.sf-wheel {
  position: fixed !important;
  /* Center of the wheel sits near the bottom-right corner */
  left: auto;
  right: calc(-0.5 * min(68vw, 520px) + 1.25rem);
  bottom: calc(-0.5 * min(68vw, 520px) + 1.25rem);
  width: min(68vw, 520px);
  height: min(68vw, 520px);
  z-index: 999 !important;
  pointer-events: none;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  opacity: 0.95;
  animation: sf-chakra 55s linear infinite;
  filter:
    saturate(1.12) contrast(1.08) brightness(1.02)
    drop-shadow(0 0 22px rgba(212, 175, 55, 0.3));
}
.sf-wheel img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: transparent !important;
}

@keyframes sf-rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes sf-shimmer {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.18); }
}
@keyframes sf-pulse {
  0%, 100% { box-shadow: 0 0 14px rgba(212, 175, 55, 0.25); }
  50% { box-shadow: 0 0 28px rgba(212, 175, 55, 0.55); }
}
@keyframes sf-chakra {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 640px) {
  .sf-brand { font-size: 2.1rem; }
  .sf-sanskrit { font-size: 1.05rem; letter-spacing: 0.1em; }
  .sf-step { min-width: 4.4rem; font-size: 0.62rem; }
  .sf-wheel {
    width: min(72vw, 340px);
    height: min(72vw, 340px);
    left: auto;
    right: calc(-0.5 * min(72vw, 340px) + 0.9rem);
    bottom: calc(-0.5 * min(72vw, 340px) + 0.9rem);
    opacity: 0.92;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sf-wheel { animation: none !important; }
  .sf-brand { animation: none !important; }
  .sf-step.is-active { animation: none !important; }
}
</style>
"""


def inject() -> None:
    import streamlit as st
    import streamlit.components.v1 as components

    # Bust cache when the asset is replaced (jpg → hollow png, etc.).
    _wheel_data_uri.cache_clear()
    uri = _wheel_data_uri()
    asset = _ASSETS / "gold_chakra.svg"
    if not asset.exists():
        asset = _ASSETS / "konark_wheel.png"
    if not asset.exists():
        asset = _ASSETS / "konark_wheel.jpg"
    ver = int(asset.stat().st_mtime)
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    # Streamlit wraps markdown in transformed containers, which breaks
    # position:fixed. Mount the chakra on parent.document.body instead.
    components.html(
        f"""
<script>
(function () {{
  const doc = window.parent.document;
  const ver = "{ver}";
  const oldStyle = doc.getElementById("sf-konark-wheel-style");
  if (oldStyle) oldStyle.remove();
  const style = doc.createElement("style");
  style.id = "sf-konark-wheel-style";
  doc.head.appendChild(style);
  // Keep size/position here so hot-reload always wins over stale CSS.
  style.textContent = `
    /* wheel-asset-v${{ver}}-br-center */
    .sf-wheel {{
      position: fixed !important;
      width: min(68vw, 520px) !important;
      height: min(68vw, 520px) !important;
      left: auto !important;
      right: calc(-0.5 * min(68vw, 520px) + 1.25rem) !important;
      bottom: calc(-0.5 * min(68vw, 520px) + 1.25rem) !important;
      opacity: 0.95 !important;
      background: transparent !important;
      background-image: none !important;
      box-shadow: none !important;
    }}
    @media (max-width: 640px) {{
      .sf-wheel {{
        width: min(72vw, 340px) !important;
        height: min(72vw, 340px) !important;
        left: auto !important;
        right: calc(-0.5 * min(72vw, 340px) + 0.9rem) !important;
        bottom: calc(-0.5 * min(72vw, 340px) + 0.9rem) !important;
      }}
    }}
  `;

  let el = doc.getElementById("sf-konark-wheel");
  if (el) el.remove();
  el = doc.createElement("div");
  el.id = "sf-konark-wheel";
  el.className = "sf-wheel";
  el.setAttribute("aria-hidden", "true");
  el.dataset.ver = ver;
  const img = doc.createElement("img");
  img.src = "{uri}";
  img.alt = "";
  el.appendChild(img);
  doc.body.appendChild(el);
}})();
</script>
""",
        height=0,
    )


def hero_html() -> str:
    # Avoid <h1>/<h2> — Streamlit rewrites those and breaks flex centering.
    return """
<div class="sf-hero">
  <p class="sf-sanskrit">साक्ष्यं धर्मः</p>
  <p class="sf-brand" role="heading" aria-level="1">SentinelFlow</p>
  <p class="sf-tagline">The Field of Evidence</p>
  <p class="sf-epigraph">
    A multi-agent cybersecurity investigation system.<br/>
    Upload a phishing email or network alert — it parses evidence, investigates with AI,<br/>
    challenges weak claims, and returns a cited incident report you can approve.
  </p>
</div>
"""


def section_html(title: str, subtitle: str = "") -> str:
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    return f'<div class="sf-section"><h2>{title}</h2>{sub}</div>'


def path_html(active: str | None = None, done: set[str] | None = None, failed: str | None = None) -> str:
    steps = [
        ("parse", "Parse"),
        ("enrich", "Enrich"),
        ("investigate", "Investigate"),
        ("critic", "Critic"),
        ("report", "Report"),
        ("approve", "Approve"),
    ]
    done = done or set()
    parts = ['<div class="sf-path">']
    for key, label in steps:
        cls = "sf-step"
        if failed and key == failed:
            cls += " is-fail"
        elif active and key == active:
            cls += " is-active"
        elif key in done:
            cls += " is-done"
        parts.append(f'<div class="{cls}">{label}</div>')
    parts.append("</div>")
    return "".join(parts)
