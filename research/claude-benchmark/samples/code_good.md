```python
import re

_PATTERN = re.compile(r"\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?\s*", re.IGNORECASE)


def parse_duration(s: str) -> int:
    if not isinstance(s, str) or not s.strip():
        raise ValueError("empty duration")
    m = _PATTERN.fullmatch(s)
    if not m or not any(m.groups()):
        raise ValueError(f"invalid duration: {s!r}")
    h, mi, se = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + se
```
