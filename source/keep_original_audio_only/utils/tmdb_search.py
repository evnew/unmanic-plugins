import importlib
from keep_original_audio_only.classes.Movie import Movie
from keep_original_audio_only.utils.path_parser import extract_years_and_titles_from_path
from keep_original_audio_only.utils.criteria_checker import does_movie_match_criteria
tmdb = importlib.import_module("keep_original_audio_only.site-packages.tmdbsimple")

def lookup_movie(path, api_key):
    tmdb.API_KEY = api_key
    years, potential_titles = extract_years_and_titles_from_path(path)
    target_year = int(years[0]) if years else None
    return next((m for m in search_tmdb_for_movies(potential_titles, target_year) if does_movie_match_criteria(m, potential_titles, years)), None)

def search_tmdb_for_movies(titles, target_year):
    if target_year is None:
        return []

    movies = []
    search = tmdb.Search()
    for title in titles:
        response = search.movie(query=title)
        closest_movie = None
        min_year_diff = float('inf')
        for result in search.results:
            movie = Movie(result)
            if movie.release_year:
                year_diff = abs(movie.release_year - target_year)
                if year_diff < min_year_diff:
                    closest_movie = movie
                    min_year_diff = year_diff
        if closest_movie:
            movies.append(closest_movie)
    return movies