BG = "#1e1f22"
BG_CARD = "#2b2d31"
BG_ELEVATED = "#313338"
BG_HOVER = "#35373c"
BG_SELECTED = "#3f4248"
BG_INPUT = "#383a40"
BORDER = "#111214"

TEXT = "#dbdee1"
TEXT_MUTED = "#949ba4"
TEXT_FAINT = "#6d6f78"

ACCENT = "#5865f2"
ACCENT_HOVER = "#4752c4"
ACCENT_ACTIVE = "#3c45a5"

DANGER = "#ed4245"
DANGER_HOVER = "#c93b3e"
SUCCESS = "#57f287"
SUCCESS_DIM = "#2b7a4b"
AUTHOR = "#8ab4f8"

FONT_FAMILY = ("Segoe UI", "Helvetica", "DejaVu Sans")
MONO_FAMILY = ("Cascadia Code", "Consolas", "DejaVu Sans Mono")


def font(size: int = 11, weight: str = "normal"):
    return (FONT_FAMILY, size, weight)


def mono(size: int = 10):
    return (MONO_FAMILY, size)
