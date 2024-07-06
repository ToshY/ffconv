from rich.console import Console
from rich.table import Table


def table_print_stream_options(tracks: list) -> None:
    """
    Prints a table of stream options for the given list of tracks.

    Parameters:
        tracks (List[Dict[str, Any]]): A list of dictionaries representing the tracks.
            Each dictionary should have keys corresponding to the column headers and values
            representing the corresponding values for each track.

    Returns:
        None
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
