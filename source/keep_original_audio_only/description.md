In the plugin settings, specify an API key for The Movie Database.
This is necessary to perform movie and tv lookups.

By default, the plugin will remove all audio tracks that do not match whatever TMdb reports as the original language.

Optionally, specify a comma-delimited list of language codes you want to keep, regardless of if they are the movie's original language. 

For example, if the movie's primary language is korean, but you want to keep an english dub (if any exist), you can add "en" to this field. The plugin will remove all languages that are not in Korean or english.

If only one audio track is found, the plugin will not remove it (regardless of whether or not it's the original language or in the languages-to-keep list).

Examples of strings to add to the languages-to-keep list:
- 'en'
- 'fr'
- 'de'