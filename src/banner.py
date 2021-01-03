# -*- coding: utf-8 -*-
"""
Created on Thu Dec  12 20:52:08 2020

@author: ToshY
"""

import pyfiglet
from pathlib import Path
from rich import print

def cli_banner(
    current_file: str,
    banner_font: str = "isometric3",
    banner_width: int = 200
) -> None:
    """
    CLI banner

    Parameters
    ----------
    current_file : str
        Main file.
    banner_font : str, optional
        Banner font type. The default is "isometric3".
    banner_width : int, optional
        Banner width. The default is 200.

    Returns
    -------
    None.

    """
    banner = pyfiglet.figlet_format(
        Path(current_file).stem, font=banner_font, width=banner_width
    )
    print(f"[bold magenta]{banner}[/bold magenta]")
