# def aggregate_text(lines: list[str]) ->str:
#     cleaned_lines = [line.strip() for line in lines if line.strip()] 
#     return "\n".join(cleaned_lines)

# Post processing?
import re

def is_nonsense(line):
    if re.search(r'\b(\w+)\b(?:\s+\1\b){2,}', line):
        return True
    if len(re.sub(r'[^a-zA-Z]', '', line)) < 5:
        return True
    words = line.split()
    if len(words) > 3 and len(set(words)) == 1:
        return True
    return False

def aggregate_text(lines: list[str]) -> str:
    cleaned_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line or is_nonsense(line):
            continue
        if line in seen:
            continue
        seen.add(line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)