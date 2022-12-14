# -*- coding: utf-8 -*-

import sys
import subprocess as sp
from loguru import logger
from rich import print
from src.exception import FFmpegError, MKVmergeError, MKVextractError, ProcessError


class Logger:
    """ Logger """

    def __init__(self, origin, verbose, rotation="5 MB"):
        logger.add(
            sys.stderr, format="{time} {level} {message}", filter=origin, level="INFO"
        )
        logger.add(f"./log/{origin}.log", rotation=rotation)
        self.logger = logger


class ProcessDisplay:
    """ Subprocess console display """

    def __init__(self, logger):
        self.logger = logger
        self.process_exceptions = {
            "ffmpeg": FFmpegError,
            "mkvmerge": MKVmergeError,
            "mkvextract": MKVextractError,
            "custom": ProcessError,
        }

        self.colors = {"ok": "green", "busy": "cyan"}

    def run(self, process, command, process_color="#F79EDE"):
        print(
            f"> The following [{process_color}]{process}[/{process_color}] command will be executed:\r"
        )
        print(f"[{self.colors['ok']}]{' '.join(command)}[/{self.colors['ok']}]")
        print(
            f"\r> [{process_color}]{process}[/{process_color}] [{self.colors['busy']}]running...[/{self.colors['busy']}]",
            end="\r",
        )

        response = sp.run(command, stdout=sp.PIPE, stderr=sp.PIPE)
        return_code = response.returncode
        if return_code == 0:
            print(
                f"> [{process_color}]{process}[/{process_color}] [{self.colors['ok']}]completed[/{self.colors['ok']}]!\r\n"
            )
            return response

        if command[0] not in self.process_exceptions:
            exception = self.process_exceptions["custom"]
        else:
            exception = self.process_exceptions[command[0]]

        self.logger.critical(response)
        raise exception(
            "Process returned exit code `{return_code}`.\r\n\r\n"
            + response.stderr.decode("utf-8")
        )
