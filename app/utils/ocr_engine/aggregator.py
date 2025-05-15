def aggregate_text(lines: list[str]) ->str:
    cleaned_lines = [line.strip() for line in lines if line.strip()] 
    return "\n".join(cleaned_lines)
