import re

def clean_title(title):
    return re.sub(r"_|[^\w\s']", ' ', title).strip()

def remove_non_title_words(words):
    with open("mediainfo_and_formatting_terms.txt", "r") as f:
        non_title_words = {l.lower() for l in f if l.strip()}
    return [w for w in words if w.lower() not in non_title_words and not re.match(r'\d{3,4}p', w.lower())]
