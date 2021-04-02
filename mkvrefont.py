# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 20:57:11 2020

@author: ToshY

MKVfonts - Remuxing attachments from folder into MKV

# Example
python mkvattach.py -i "./input/myfile.mkv" -o "./output" -f "./input/fonts"
"""

import sys
import argparse
import subprocess as sp
from pathlib import Path, PurePath
from src.banner import cli_banner
from src.simulate import SimulateLoading
from src.args import files_in_dir
from src.fonts import FontFinder
from src.args import FileDirectoryCheck, files_in_dir
from src.general import remove_suffix_from_string
from rich import print
from rich.prompt import IntPrompt
from langcodes import standardize_tag
from src.logger import Logger, ProcessDisplay
from loguru import logger


def cli_args(args=None):
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
        "-m",
        "--mode",
        type=str,
        required=True,
        choices=["add", "replace"],
        default=["replace"],
        nargs="+",
        help="Mode to add attachments to existing file or remove existing attachments and add new attachments",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Verbose logging",
    )

    if args is not None:
        args = parser.parse_args(args)
    else:
        args = parser.parse_args()

    # Check args
    user_args = check_args(args.input, args.output, args.mode)

    return user_args, args.verbose


def check_args(inputs, outputs, mode):
    """
    Check the amount of input arguments, outputs and presets.

    Parameters
    ----------
    inputs : list
        Input argument(s).
    outputs : list
        Output arugment(s).
    vpresets : list
        Video preset argument(s).
    apresets : list
        Audio preset argument(s).

    Raises
    ------
    Exception
        Input arguments not equals the amount of other arguments (and is not equal to 1).

    Returns
    -------
    None.

    """

    len_inputs = len(inputs)
    len_outputs = len(outputs)

    if len_inputs != len_outputs:
        if len_outputs != 1:
            raise Exception(
                f"Amount of input arguments ({len_inputs}) "
                "does not equal the amount of output arguments ({len_outputs})."
            )

    if mode is not None:
        len_mode = len(mode)
        if len_mode != 1:
            if len_inputs != len_mode:
                raise Exception(
                    f"Amount of input arguments ({len_inputs}) "
                    "does not equal the amount of mode arguments ({len_mode})."
                )

            mdata = []
            for mp in mode:
                mdata.append(mp)
        else:
            mdata = mode[0]
    else:
        len_mode = 0
        mdata = [
            "replace",
        ]

    # Prepare inputs/outputs/presets
    batch = {}
    for i, el in enumerate(inputs):

        cpath = [*el][0]
        ptype = str(*el.values())

        if ptype == "file":
            all_files = [Path(cpath)]
        elif ptype == "directory":
            all_files = files_in_dir(cpath)

        len_all_files_in_batch = len(all_files)

        if len_outputs == 1:
            output_files = [[*outputs][0]]
            output_type = str(*outputs[0].values())
            if ptype == "directory":
                if len_all_files_in_batch > len_outputs and output_type == "file":
                    raise Exception(
                        f"The path `{cpath.as_posix()}` contains"
                        f" `{len_all_files_in_batch}` files but only"
                        f" `{len_outputs}`"
                        f" output filename(s) was/were specified."
                    )
                else:
                    output_files = [outputs[0] for x in range(len(all_files))]
        else:
            output_files = outputs[0]
            # Unset
            outputs.pop(0)
            # Check type
            if ptype == "directory":
                # Create copies
                output_files = [output_files for x in range(len(all_files))]

        if len_mode == 1:
            mode_data = mdata
            mode_data = [mode_data for x in range(len(all_files))]
        else:
            if len_mode == 0:
                mode_data = mdata
                mode_data = [mode_data for x in range(len(all_files))]
            else:
                mode_data = mdata[0]
                mdata.pop(0)
                mode_data = [mode_data for x in range(len(all_files))]

        batch[str(i)] = {
            "input": all_files,
            "output": output_files,
            "mode": mode_data,
        }

    return batch


def remux_file(input_file, output_dir, new_file_suffix=" (1)"):
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

    # Output argument
    output_path = list(output_dir[0].keys())[0]
    output_type = list(output_dir[0].values())[0]
    output_file_name = input_file.stem + new_file_suffix + input_file.suffix

    # File attachments/subtitles directory
    file_attachments_dir = input_file.with_suffix("")
    if file_attachments_dir.as_posix().endswith("_stripped"):
        file_attachments_dir = Path(
            remove_suffix_from_string(file_attachments_dir.as_posix(), "_stripped")
        )
        output_file_name = (
            file_attachments_dir.stem + new_file_suffix + input_file.suffix
        )

    if not file_attachments_dir.exists():
        raise Exception(
            f"The file does not have a corresponding directory `{file_attachments_dir}`!"
        )

    # Fonts directory
    file_attachments_font_dir = file_attachments_dir.joinpath("attachments")
    if not file_attachments_font_dir.exists():
        raise Exception(
            f"No `attachments` folder found in `{file_attachments_dir}`! Please put your fonts in an `attachments` folder."
        )

    # Read font files
    fonts = files_in_dir(file_attachments_font_dir, ["*.ttf", "*.otf", "*.eot"])

    # Get MKV font arguments
    mkv_fonts = font_attachments(fonts)

    # Read subtitles files
    subtitles = files_in_dir(file_attachments_dir, ["*.ass", "*.srt"])

    # Get MKV subtitle arguments
    mkv_subtitles = subtitle_attachments(subtitles)

    # Prepare output file
    if output_type == "directory":
        output_file = output_path.joinpath(output_file_name).as_posix()
    else:
        output_file = output_path.with_suffix("").as_posix()

    mkvremux_cmd = (
        ["mkvmerge", "--output", output_file, "(", input_file.as_posix(), ")",]
        + mkv_subtitles
        + mkv_fonts
    )

    process = ProcessDisplay(logger)
    result = process.run("MKVmerge remux", mkvremux_cmd)

    return mkvremux_cmd


def strip_file_attachments(input_file: Path) -> Path:
    """
    Strip attachments, subtitles, tags and chapters and create temporary file

    Parameters
    ----------
    input_file : Path
        DESCRIPTION.

    Raises
    ------
    Exception
        DESCRIPTION.

    Returns
    -------
    None.

    """

    temporary_file = input_file.parent.joinpath(
        input_file.stem + "_stripped" + input_file.suffix
    )

    mkvmerge_cmd = [
        "mkvmerge",
        "--output",
        temporary_file.as_posix(),
        "--no-subtitles",
        "--no-attachments",
        "--no-chapters",
        "--no-track-tags",
        "--no-global-tags",
        "(",
        input_file.as_posix(),
        ")",
    ]

    process = ProcessDisplay(logger)
    result = process.run("MKVmerge strip", mkvmerge_cmd)

    return temporary_file


def font_attachments(fonts_list):
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
            font.as_posix(),
        ]

    return mkv_fonts


def subtitle_attachments(subtitle_list):
    """

    Parameters
    ----------
    fonts_list : list
        List of subtitle Path objects

    Returns
    -------
    mkv_subtitles : list
        List of MKVmerge attachment commands

    """

    mkv_subtitles = []
    for subtitle in subtitle_list:
        mkv_subtitles = mkv_subtitles + [
            "--language",
            "0:" + standardize_tag(subtitle.with_suffix("").as_posix()[-3:]),
            "(",
            subtitle.as_posix(),
            ")",
        ]

    return mkv_subtitles


@logger.catch
def main(custom_args=None):
    # Input arguments
    user_args, verbose = cli_args(custom_args)

    # Logger
    global logger
    logger = Logger(Path(__file__).stem, verbose).logger

    for x, b in user_args.items():
        for y, fl in enumerate(b["input"]):
            # Check if first/last item for reporting
            if fl == b["input"][0]:
                m = 0
            elif fl == b["input"][-1]:
                m = 1
            else:
                m = None

            # In replace mode, strip subtitles, attachments, tags and chapters
            if b["mode"][y] == "replace":
                fl = strip_file_attachments(fl)

            # Remux file attachments
            remux_file(fl, b["output"])


if __name__ == "__main__":
    """ Main """
    cli_banner(__file__)

    # Stop execution at keyboard input
    try:
        # Call main
        main_result = main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        exit()
