from __future__ import annotations

ACCESSIBILITY_CSS = """
:root {
    --ius-focus-ring: #0b5fff;
    --ius-content-width: 92rem;
    --ius-touch-target: 44px;
}

.ier-skip-link {
    position: fixed;
    top: 0.5rem;
    left: 0.5rem;
    z-index: 99999;
    transform: translateY(-180%);
    padding: 0.65rem 0.9rem;
    border-radius: 0.45rem;
    background: #ffffff;
    color: #111111;
    border: 2px solid #111111;
    font-weight: 700;
}

.ier-skip-link:focus {
    transform: translateY(0);
}

[data-testid="stAppViewContainer"] .main .block-container {
    max-width: var(--ius-content-width);
    padding-top: 1.25rem;
    padding-bottom: 3rem;
}

button,
[role="button"],
input:not([type="checkbox"]):not([type="radio"]),
textarea,
select {
    min-height: var(--ius-touch-target);
}

button:focus-visible,
[role="button"]:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[tabindex]:focus-visible {
    outline: 3px solid var(--ius-focus-ring) !important;
    outline-offset: 3px !important;
}

[data-testid="stDataFrame"] {
    overflow-x: auto;
}

.ier-section-context {
    margin: 0 0 1rem;
    padding: 0.65rem 0.8rem;
    border-left: 0.25rem solid currentColor;
    border-radius: 0.25rem;
}

@media (max-width: 48rem) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-left: 0.9rem;
        padding-right: 0.9rem;
        padding-top: 0.8rem;
    }

    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        gap: 0.75rem;
    }

    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }

    [data-testid="stMetric"] {
        min-width: 100%;
    }

    h1 {
        font-size: clamp(1.75rem, 9vw, 2.35rem);
    }

    h2 {
        font-size: clamp(1.35rem, 7vw, 1.8rem);
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
    }
}
"""


def accessibility_css() -> str:
    """Devuelve la hoja de estilos accesible y responsiva."""

    return ACCESSIBILITY_CSS.strip()
