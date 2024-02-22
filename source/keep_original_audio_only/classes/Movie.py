import importlib
from datetime import datetime
from utils.language_codes import language_codes
tmdb = importlib.import_module("keep_original_audio_only.site-packages.tmdbsimple")

class Movie:
    def __init__(self, obj):
        self.id = obj['id']
        self.title = obj['title']
        self.release_year = self._parse_date(obj.get('release_date', ''))

        self.info = self._get_movie_info()
        original_language = self.info.get("original_language")
        self.original_language_639_1 = original_language
        
        if original_language in language_codes.keys():
            self.original_language_639_2 = language_codes[self.original_language_639_1]
        else:
            self.original_language_639_2 = None

    def __eq__(self, other):
        return self.id == other.id
    
    def __hash__(self):
        return hash(('id', self.id))

    def _parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').year
        except ValueError:
            return None
        
    def _get_movie_info(self):
        movie = tmdb.Movies(self.id)
        return movie.info()
    