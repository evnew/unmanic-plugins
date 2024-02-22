import os
import re
from keep_original_audio_only.utils.cleaner import clean_title

def extract_years_and_titles_from_path(path):
    parts = path.split(os.sep)
    file_name = parts.pop()
    folder_name = parts.pop()
    string = folder_name + ' ' + os.path.splitext(file_name)[0]

    potential_years = set()
    potential_titles = set([folder_name, file_name])

    matches = re.findall(r'[^0-9](19\d{2}|20\d{2})([^0-9p]|$)', string)
    for match in matches:
        match = ''.join([c for c in match if c.isdigit()])
        if len(match) == 4:
            potential_years.add(match)
            potential_titles = {re.sub(match, '', t) for t in potential_titles}

    potential_titles = {clean_title(t) for t in potential_titles if clean_title(t)}
    return list(potential_years), list(potential_titles)