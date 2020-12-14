# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 23:03:08 2020

@author: ToshY

SimulateLoading - Simulate loading in command line with spinner
"""

import sys
import time


class SimulateLoading:
    """ Animate spinner when commands are running, e.g. FFprobe/MKVmerge """

    def __init__(self, process_name="process"):
        self.pname = process_name

    def check_probe(self, probe):
        """ Check the running process and show spinner with optional text """

        sys.stdout.write("\r\n")
        while probe.poll() is None:
            sys.stdout.write("\r")
            self.spinner()
            sys.stdout.write(f"{self.pname}".format(self.pname))
            sys.stdout.flush()
        sys.stdout.write(f"\r{self.pname} - complete!")

        return probe.poll()

    def spinner(self, chars="/—\|", wait=0.075):
        """ Anime loading with specified characters """

        for char in chars:
            sys.stdout.write("\r" + char + " ")
            time.sleep(wait)
            sys.stdout.flush()
