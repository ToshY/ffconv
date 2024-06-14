import pyfiglet
from pathlib import Path
from rich import print


def cli_banner(
    current_file: str, banner_font: str = "isometric3", banner_width: int = 200
) -> None:
    """
    Print a banner with the file name using the pyfiglet library.

    Args:
        current_file (str): The path to the current file.
        banner_font (str, optional): The font to use for the banner. Defaults to "isometric3".
        banner_width (int, optional): The width of the banner. Defaults to 200.

    Returns:
        None: This function does not return anything.

    """
    file_name = Path(current_file).stem

    banner = pyfiglet.figlet_format(file_name, font=banner_font, width=banner_width)
    print(f"[bold magenta]{banner}[/bold magenta]")
