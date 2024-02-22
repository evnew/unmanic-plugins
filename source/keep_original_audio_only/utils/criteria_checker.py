import re

def does_movie_match_criteria(movie, titles, years):
    tmdb_title_clean = re.sub(r'[^a-zA-Z0-9]', '', movie.title).lower()
    src_titles = {re.sub(r'[^a-zA-Z0-9]', '', t).lower() for t in titles}
    return tmdb_title_clean in src_titles or any(int(year) == movie.release_year for year in years)
