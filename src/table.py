# -*- coding: utf-8 -*-
"""
Created on Thu Dec  12 20:52:08 2020

@author: ToshY
"""

from rich.console import Console
from rich.table import Table


def table_print_stream_options(tracks: list) -> None:
    """
    Print a table with specified stream options.

    Parameters
    ----------
    tracks : list
        A list of dictonaries with specific stream values.

    Returns
    -------
    None.
    """

    table = Table(show_header=True, header_style="bold cyan")

    # Header
    for key in tracks[0].keys():
        table.add_column(key.capitalize())

    # Rows
    for track in tracks:
        table.add_row(*[str(val) for val in list(track.values())])

    console = Console()
    console.print(table)
