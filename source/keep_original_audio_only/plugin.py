#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>, senorsmartypants@gmail.com
    Date:                     20 Sep 2021, (10:45 PM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import os
import sys
import logging
import mimetypes

from unmanic.libs.system import System
from unmanic.libs.unplugins.settings import PluginSettings

from keep_original_audio_only.utils.tmdb_search import lookup_movie
from keep_original_audio_only.classes.Movie import Movie
from keep_original_audio_only.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.tmdb_default_audio_to_original_language")


class Settings(PluginSettings):
    settings = {
        "tmdb_api_key": "",
        "languages_to_keep": "",
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)

        self.form_settings = {
            "tmdb_api_key": {
                "label": "API Key for The Movie Database",
            },
            "languages_to_keep": {
                "label": "Audio languages to keep (even if they aren't in the movie's original langauge)",
            },
        }

class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, ['video', 'audio', 'data'])
        self.settings = None
        self.languages_to_remove = []
        

    def set_settings(self, settings):
        self.settings = settings

    def set_settings(self, settings, original_language):
        self.settings = settings
        self.original_language = original_language

    def set_audio_stream_to_remove(self, lang):
        self.languages_to_remove.append(lang)

    def get_languages_to_remove(self):
        return self.languages_to_remove

    def test_tags_for_search_string(self, codec_type, stream_tags, stream_id):
        if stream_tags and True in list(k.lower() in ['title', 'language'] for k in stream_tags):
            
            if codec_type != 'audio' or self.audio_stream_count == 1:
                return False
                
            language_list = self.settings.get_setting('languages_to_keep')
            languages = list(filter(None, language_list.split(',')))
            languages.append(self.original_language)
            languages = [l.strip().lower() for l in languages]

            logger.debug("Languages to keep: {}".format(languages))
            logger.debug("Language found: {}".format(stream_tags.get('language', '').lower()))

            for stream in stream_tags.get('language', '').lower():
                stream = stream.strip()
                if stream and stream.lower() not in languages:
                    # Found a matching language. Process this stream to remove it
                    self.set_audio_stream_to_remove(stream)                    
        else:
            logger.warning(
                "Stream #{} in file '{}' has no 'language' tag. Ignoring".format(stream_id, self.input_file))
        return self.languages_to_remove and len(self.languages_to_remove) > 0

    def test_stream_needs_processing(self, stream_info: dict):
        """Only add streams that have language task that match our list"""
        return self.test_tags_for_search_string(stream_info.get('codec_type', '').lower(), stream_info.get('tags'), stream_info.get('index'))

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        """Remove this stream"""
        return {
            'stream_mapping':  [],
            'stream_encoding': [],
        }


def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # If the config is empty (not yet configured) ignore everything
    if not settings.get_setting('tmdb_api_key'):
        logger.debug("Plugin has not yet been configured with an API key for TMdb.")
        return False

    # Get the path to the file
    abspath = data.get('path')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    movie = lookup_movie(abspath, settings.get_setting('tmdb_api_key'))
    if not movie or not movie.original_language_639_1:
        logger.debug("TMdb movie lookup returned no valid results.")
        data['issues'].append({
            'id':      'keep_original_audio_only',
            'message': "TMdb movie lookup returned no valid results. Cannot determine original language.",
        })
        return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_settings(settings, movie.original_language_639_1)
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    if mapper.streams_need_processing():
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. Probe found streams require processing.".format(abspath))
    else:
        logger.debug("File '{}' does not contain streams that require processing.".format(abspath))

    del mapper

    return data

def remove_languages(mapper):
    for language in mapper.get_languages_to_remove():
        language = language.strip()
        if language and language.lower():
            mapper.stream_mapping += ['-map', '-0:a:m:language:{}'.format(language)]

def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:

    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    movie = lookup_movie(abspath, settings.get_setting('tmdb_api_key'))
    if not movie or not movie.original_language_639_1:
        logger.debug("TMdb movie lookup returned no valid results.")
        data['issues'].append({
            'id':      'keep_original_audio_only',
            'message': "TMdb movie lookup returned no valid results. Cannot determine original language.",
        })
        return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_settings(settings, movie.original_language_639_1)
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    if mapper.streams_need_processing():
        # Set the output file
        mapper.set_output_file(data.get('file_out'))

        # clear stream mappings, copy everything
        mapper.stream_mapping = ['-map', '0']
        mapper.stream_encoding = ['-c', 'copy']

        # set negative stream mappings to remove languages
        remove_languages(mapper)

        # Get generated ffmpeg args
        ffmpeg_args = mapper.get_ffmpeg_args()

        # Apply ffmpeg args to command
        data['exec_command'] = ['ffmpeg']
        data['exec_command'] += ffmpeg_args

        # Set the parser
        parser = Parser(logger)
        parser.set_probe(probe)
        data['command_progress_parser'] = parser.parse_progress

    return data
