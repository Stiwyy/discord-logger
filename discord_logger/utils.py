import re


def clean_name(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name)
    return re.sub(r"[\s-]+", "_", s) or "default"
