# -*- coding: utf-8 -*-
"""
Created on Fri Apr  2 15:04:43 2021

@author: ToshY
"""


class FontNotFoundError(Exception):
    """Exception raised when font is not found"""

    pass


class InvalidASSFormatLines(Exception):
    """Exception raised when the amount of Format tags count exceed 2 in the subtitle file"""

    pass


class InvalidSubtitleFormatLines(Exception):
    """Exception raised when the amount of Format tags count exceed 2 in the subtitle file"""

    pass


class SubtitleNotFoundError(Exception):
    """Exception raised when no subtitle stream was found in the video file"""

    pass


class FFmpegError(Exception):
    """Exception raised when FFmpeg probe or conversion fails"""


class MKVmergeError(Exception):
    """Exception raised when MKVmerge identify or remux fails"""


class MKVextractError(Exception):
    """Exception raised when MKVextract fails"""


class ProcessError(Exception):
    """Exception raised when a custom subprocess fails"""
