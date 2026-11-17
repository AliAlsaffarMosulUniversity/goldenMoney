```python
def parse_duration(s: str) -> int:
    total = 0
    for num, unit in __import__("re").findall(r"(\d+)([hms])", s.lower()):
        total += int(num) * {"h": 3600, "m": 60, "s": 1}[unit]
    return total
```
