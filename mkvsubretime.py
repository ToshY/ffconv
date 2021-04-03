# -*- coding: utf-8 -*-
"""
Created on Sat Apr  3 17:11:38 2021

@author: ToshY

Example Scenedetect
scenedetect --input "input.mkv" --stats "input.stats.csv" detect-content --threshold 30 list-scenes save-images --output "images"

"""

from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector


def find_scenes(video_path, threshold=30.0):
    # Create our video & scene managers, then add the detector.
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold))

    # Improve processing speed by downscaling before processing.
    video_manager.set_downscale_factor()

    # Start the video manager and perform the scene detection.
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    # Each returned scene is a tuple of the (start, end) timecode.
    return scene_manager.get_scene_list()