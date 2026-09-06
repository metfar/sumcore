#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#  
#  Copyright 2018- William Martinez Bas <metfar@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
from .architecture import DEFAULT_ARCHITECTURE, write_architecture_artifacts;
from .compat import FALSE_ALIASES, NULL_ALIASES, TRUE_ALIASES, basic_boolean, is_null_alias, truth_alias;
from .audio import AudioEngine;
from .audio_api import audio_engine, beep, play, set_audio_engine, sound, stop_audio, wait_audio;
__version__ = "0.1.0a9";
__all__ = ["DEFAULT_ARCHITECTURE", "write_architecture_artifacts", "TRUE_ALIASES", "FALSE_ALIASES", "NULL_ALIASES", "truth_alias", "is_null_alias", "basic_boolean", "AudioEngine", "audio_engine", "beep", "play", "set_audio_engine", "sound", "stop_audio", "wait_audio"];
