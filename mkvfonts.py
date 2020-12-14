# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 20:57:11 2020

@author: ToshY

MKVfonts - Remuxing fonts from folder into MKV

# Example
python mkvfonts.py -i "./input/myfile.mkv" -o "./output" -f "./input/fonts"
"""

import argparse
import subprocess as sp
from src.banner import cli_banner
from src.simulate import SimulateLoading
from src.args import files_in_dir
from src.fonts import FontFinder
from src.args import FileDirectoryCheck


def cli_args():
    """
    Command Line argument parser

    Returns
    -------
    str
        The path of the input file/directory
    str
        The path of the output directory
    tuple
        The tuple to sort on key for each track in the accompagnied stream

    """

    # Arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        action=FileDirectoryCheck,
        nargs="+",
        help="Path to input file or directory",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        action=FileDirectoryCheck,
        nargs="+",
        help="Path to output directory",
    )

    parser.add_argument(
        "-f",
        "--fonts",
        type=str,
        required=False,
        action=FileDirectoryCheck,
        nargs="+",
        help="Path to add additional fonts",
    )

    parser.add_argument(
        "-s",
        "--subtitles",
        type=str,
        required=False,
        action=FileDirectoryCheck,
        nargs="+",
        help="Path to add additional subtitles",
    )

    args = parser.parse_args()

    return args.input, args.output, args.fonts, args.subtitles


def remux_file(input_file, output_dir, fonts, new_file_suffix=" (1)"):
    """
    Remuxing file with specified fonts

    Parameters
    ----------
    input_file : Path
        The specified input file as Path object
    output_dir : Path
        The specified output directory as Path object
    fonts : List
        List of font files as Path objects
    new_file_suffix : str, optional
        Suffix used for filenaming. The default is ' (1)'.

    Returns
    -------
    None.

    """

    mkv_fonts = mkv_font_attachments(fonts)

    # Prepare output file
    if output_dir["type"] == "directory":
        output_file = str(
            output_dir["path"].joinpath(
                input_file.stem + new_file_suffix + input_file.suffix
            )
        )
    else:
        output_file = str(
            output_dir["path"].parent.joinpath(
                input_file.stem + new_file_suffix + input_file.suffix
            )
        )

    input_file_str = str(input_file)
    mkv_cmd = [
        "mkvmerge",
        "--output",
        output_file,
        "(",
        input_file_str,
        ")",
    ] + mkv_fonts
    mkv_cmd_verbose = " ".join(mkv_cmd)
    print("\r\n\r\n> The following MKVmerge command will be executed:\r\n")
    print(mkv_cmd_verbose)

    try:
        cprocess = sp.Popen(mkv_cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        # Animate process in terminal
        SL = SimulateLoading("Remuxing")
        return_code = SL.check_probe(cprocess)

        if return_code != 0:
            raise Exception("MKVmerge returned exit code `{}`.".format(return_code))

        return return_code
    except Exception as e:
        raise (
            "An error occured while trying to remux your file:\n\r{}".format(
                e.output.decode("utf-8")
            )
        )

    return mkv_cmd


def mkv_font_attachments(fonts_list):
    """

    Parameters
    ----------
    fonts_list : list
        List of font Path objects

    Returns
    -------
    mkv_fonts : list
        List of MKVmerge attachment commands

    """

    mkv_fonts = []
    for font in fonts_list:
        mkv_fonts = mkv_fonts + [
            "--attachment-name",
            font.name,
            "--attachment-mime-type",
            FontFinder.mimetype_by_extension(font.suffix),
            "--attach-file",
            str(font),
        ]

    return mkv_fonts


def check_input_in_dir(user_input):
    if user_input["type"] == "file":
        all_files = [user_input["path"]]
    elif user_input["type"] == "directory":
        all_files = files_in_dir(user_input["path"])
    else:
        raise Exception(
            "[red]Invalid path type [cyan]{input_type}[/cyan][/red]".format(
                input_type=user_input["type"]
            )
        )

    return all_files


def main():
    # Input arguments
    inputs, output, fonts, subtitles = cli_args()

    # Remove Nones
    all_inputs = check_input_in_dir(inputs)
    all_fonts = check_input_in_dir(fonts)
    all_subtitles = []
    if subtitles is not None:
        all_subtitles = check_input_in_dir(subtitles)

    for fl in all_inputs:
        remux_file(fl, output, all_fonts, new_file_suffix=" (1)")


if __name__ == "__main__":
    """ Main """
    cli_banner(__file__)

    # Stop execution at keyboard input
    try:
        resl = main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        pass
