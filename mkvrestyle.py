# -*- coding: utf-8 -*-
"""
Created on Sat Nov 14 17:11:27 2020

@author: ToshY

MKVrestyle - Restyle the main font styling of the embedded ASS file

# Example
python mkvrestyle.py -i "./input/" -o "./output/" -sp "./preset/subtitle_preset.json"
"""

import os
import re
import sys
import argparse
import mimetypes
import json
import pyfiglet
import subprocess as sp
import functools as fc
from operator import itemgetter
from pathlib import Path
from src.simulate import SimulateLoading
from src.fonts import FontFinder
from rich import print
from rich.prompt import IntPrompt
from rich.console import Console
from rich.table import Table


class DirCheck(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        all_values = []
        for fl in values:
            p = Path(fl).resolve()
            if not p.exists():
                raise FileNotFoundError(
                    f"[red]The specificed path `{fl}` does not exist.[/red]"
                )
            if p.is_file():
                all_values.append({p: "file"})
                continue
            all_values.append({p: "directory"})

        setattr(args, self.dest, all_values)


class ExtCheck(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        mimetypes.init()
        stripped_ext = values.lstrip(".")
        ext_check = "placeholder." + stripped_ext
        mime_output = mimetypes.guess_type(ext_check)[0]
        if "video" not in mime_output:
            raise ValueError(
                f"[red]The specificed output extension `{stripped_ext}` is not a valid video extension.[/red]"
            )
        setattr(args, self.dest, {"extension": stripped_ext})


def cli_banner(banner_font="isometric3", banner_width=200):
    banner = pyfiglet.figlet_format(
        Path(__file__).stem, font=banner_font, width=banner_width
    )
    print(f"[bold magenta]{banner}[/bold magenta]")


def cli_args():
    """
    Command Line argument parser.

    Returns
    -------
    str
        The path of the input file/directory.
    str
        The path of the output directory.
    tuple
        The tuple to sort on key for each track in the accompagnied stream.

    """

    # Banner
    cli_banner()

    # Arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        action=DirCheck,
        nargs="+",
        help="Path to input file or directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        action=DirCheck,
        nargs="+",
        help="Path to output directory",
    )
    parser.add_argument(
        "-ss",
        "--stream_select",
        type=str,
        required=False,
        nargs="+",
        help="Stream select by id or 3 letter language code",
    )
    parser.add_argument(
        "-sp",
        "--subtitle_preset",
        type=str,
        required=True,
        action=DirCheck,
        nargs="+",
        help="Path to JSON file with ASS video preset options",
    )
    parser.add_argument(
        "-w",
        "--overwrite",
        type=int,
        default=[1],
        nargs="+",
        help="Overwrite existing file with modified ASS styling",
    )
    args = parser.parse_args()

    # Check args count
    user_args = check_args(
        args.input,
        args.output,
        args.stream_select,
        args.subtitle_preset,
        args.overwrite,
    )

    return user_args


def check_args(inputs, outputs, stream_select, spresets, overwrites):
    """
    Check the amount of input arguments, outputs and presets.

    Parameters
    ----------
    inputs : list
        Input argument(s).
    outputs : list
        Output arugment(s).
    stream_select: list
        Subtitle stream select argument(s)
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
                f"[red]Amount of input arguments ({len_inputs}) does not equal the amount of output arguments ({len_outputs}).[/red]"
            )

    if stream_select is not None:
        len_stream_select = len(stream_select)
        if len_stream_select != 1:
            if len_inputs != len_stream_select:
                raise Exception(
                    f"[red]Amount of input arguments ({len_inputs}) does not equal the amount of subtitle stream select arguments ({len_stream_select}).[/red]"
                )

            ssdata = []
            for op in overwrites:
                ssdata.append(list(op.keys())[0])
        else:
            ssdata = [stream_select[0]]
    else:
        len_stream_select = 0
        ssdata = ['-1']

    len_spresets = len(spresets)
    if len_spresets != 1:
        if len_inputs != len_spresets:
            raise Exception(
                f"[red]Amount of input arguments ({len_inputs}) does not equal the amount of subtitle preset arguments ({len_spresets}).[/red]"
            )

        sdata = []
        for spp in spresets:
            sdata.append(remove_empty_dict_values(read_json(list(spp.keys())[0])))
    else:
        sdata = remove_empty_dict_values(read_json(*spresets[0]))

    len_overwrites = len(overwrites)
    if len_overwrites != 1:
        if len_inputs != len_overwrites:
            raise Exception(
                f"[red]Amount of input arguments ({len_inputs}) does not equal amount of overwritable arguments ({len_overwrites}).[/red]"
            )

        odata = []
        for op in overwrites:
            odata.append(list(op.keys())[0])
    else:
        odata = [overwrites[0]]

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
                    """
                    If a batch contains a directory, and it contains more files than specified outputs, this should
                    throw an exception because it's not possible to create files with the same filename in the same
                    output directory. The user has 2 options: 
                    1. Just specify an output directory which leaves the filenames unchanged: 
                        -o "./output"
                    2. Specify all the files as seperate "batches":
                        -i './input/file_1.mkv' './input/fle_2.mkv' -o './output/file_new_1.mp4' './output/file_new_2.mp4'
                    """
                    raise Exception(
                        f"[red]The path [cyan]`{str(cpath)}`[/cyan] [red]contains"
                        f" [cyan]`{len_all_files_in_batch}`[/cyan] [red]files but only"
                        f" [cyan]`{len_outputs}`[/cyan]"
                        f" [red]output filename(s) was/were specified.[/red]"
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

        if len_spresets == 1:
            subtitle_select_stream = ssdata
            if ptype == "directory":
                subtitle_select_stream = [
                    subtitle_select_stream for x in range(len(all_files))
                ]
        else:
            if len_spresets == 0:
                subtitle_select_stream = ssdata
                if ptype == "directory":
                    subtitle_select_stream = [
                        subtitle_select_stream for x in range(len(all_files))
                    ]
            else:
                subtitle_select_stream = ssdata[0]
                ssdata.pop(0)
                if ptype == "directory":
                    subtitle_select_stream = [
                        subtitle_select_stream for x in range(len(all_files))
                    ]

        if len_spresets == 1:
            subtitle_data = sdata
            if ptype == "directory":
                subtitle_data = [subtitle_data for x in range(len(all_files))]
        else:
            if len_spresets == 0:
                subtitle_data = sdata
                if ptype == "directory":
                    subtitle_data = [subtitle_data for x in range(len(all_files))]
            else:
                subtitle_data = sdata[0]
                sdata.pop(0)
                if ptype == "directory":
                    subtitle_data = [subtitle_data for x in range(len(all_files))]

        if len_overwrites == 1:
            overwrite_data = odata
            if ptype == "directory":
                overwrite_data = [overwrite_data for x in range(len(all_files))]
        else:
            if len_overwrites == 0:
                overwrite_data = odata
                if ptype == "directory":
                    overwrite_data = [overwrite_data for x in range(len(all_files))]
            else:
                overwrite_data = odata[0]
                odata.pop(0)
                if ptype == "directory":
                    overwrite_data = [overwrite_data for x in range(len(all_files))]

        batch[str(i)] = {
            "input": all_files,
            "output": output_files,
            "subtitle_stream_select": subtitle_select_stream,
            "subtitle_preset": subtitle_data,
            "overwrite": overwrite_data,
        }

    return batch


def print_subtitle_streams_options(tracks):

    table = Table(show_header=True, header_style="bold cyan")

    # Header
    for key in tracks[0].keys():
        table.add_column(key.capitalize())

    # Rows
    for track in tracks:
        table.add_row(*[str(val) for val in list(track.values())])

    console = Console()
    console.print(table)


def files_in_dir(file_path, file_types=["*.mkv"]):
    """
    Get the files in the specified directory.

    Parameters
    ----------
    file_path : str
        Path of input directory.
    file_types : list, optional
        Allowed extension to look for. The default is ['*.mkv'].

    Returns
    -------
    flist : list
        List of Path objects in specified directory.

    """

    flist = [f for f_ in [Path(file_path).rglob(e) for e in file_types] for f in f_]

    return flist


def remove_empty_dict_values(input_dict):
    """
    Get keys from dictonary where the values are not empty.

    Parameters
    ----------
    input_dict : dict
        The specified input dictonary.

    Returns
    -------
    dict
        The input dictonary without the keys that have no empty values

    """

    cleared_data = {k: v for k, v in input_dict.items() if v}

    return cleared_data


def dict_to_list(input_dict):
    """
    Convert dictonary key/values to 1D list

    Parameters
    ----------
    input_dict : dict
        The specified input dictonary

    Returns
    -------
    ffmpeg_arglist : list
        List of key-value arguments

    """

    ffmpeg_arglist = list(fc.reduce(lambda x, y: x + y, input_dict.items()))

    return ffmpeg_arglist


def list_to_dict(input_list):
    """
    Convert list to key:value pairs

    Parameters
    ----------
    input_list : list
        The specified input list

    Returns
    -------
    output_dict : TYPE
        Dict of key-value pair

    """

    output_dict = dict(zip(input_list[::2], input_list[1::2]))

    return output_dict


def read_subs(file_name):
    """
    Read in file

    Parameters
    ----------
    file_name : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    """
    return open(str(file_name), mode="r").read().splitlines()


def read_json(input_file):
    """
    Read in JSON file.

    Parameters
    ----------
    input_file : str
        The specified input JSON file

    Returns
    -------
    data : dictonary
        The JSON read data

    """

    with open(input_file) as json_file:
        data = json.load(json_file)

    return data


def get_lines_per_type(my_lines, split_at=["Format: "]):
    return [
        (i, [x for x in re.split("|".join(split_at) + "|,", s) if x])
        for i, s in enumerate(my_lines)
        if any(s.startswith(xs) for xs in split_at)
    ]


def prepare_track_info(file, index, codec, lang):
    return file.stem + "_track" + str(index) + "_" + lang + subs_mimetype(codec)


def additional_info():
    return {"WrapStyle": "0", "ScaledBorderAndShadow": "yes", "YCbCr Matrix": "TV.709"}


def extract_subsnfonts(input_file, save_loc, stream_select):

    # file str
    input_file_str = str(input_file)
    
    mkv_cmd = [
        "mkvmerge",
        "--identify",
        "--identification-format",
        "json",
        input_file_str,
    ]
    cprocess = sp.run(mkv_cmd, capture_output=True)

    # Json output
    mkvout = json.loads(cprocess.stdout)

    # Get attachments
    attachments = mkvout["attachments"]
    tracks = mkvout["tracks"]

    ass_subs = [
        {
            "index": sub["id"],
            "codec": sub["properties"]["codec_id"],
            "language": sub["properties"]["language"],
            "title": sub["properties"]["track_name"],
            "save_file": prepare_track_info(
                input_file,
                sub["id"],
                sub["properties"]["codec_id"],
                sub["properties"]["language"],
            ),
        }
        for sub in tracks
        if sub["type"] == "subtitles"
    ]
    
    # No user input provided, so identify streams and ask for input
    if stream_select == '-1':
        selected_subs = ass_subs[0]["index"]
        # Request user input for stream type
        if len(ass_subs) > 1:
            print(f"\r\n> Multiple subtitle streams detected")
    
            # Print the options
            print_subtitle_streams_options(ass_subs)
            allowed = [str(sub["index"]) for sub in ass_subs]
    
            # Request user input
            selected_subs = IntPrompt.ask(
                "\r\n# Please specify the subtitle index to use: ",
                choices=allowed,
                default=selected_subs,
                show_choices=True,
                show_default=True,
            )
            print(f"\r> Stream index [green]`{selected_subs}`[/green] selected!")
    else:
        if stream_select.isnumeric():
            selected_subs = stream_select
        else:
            # Find index for language property; TODO make dynamic property
            selected_subs = next(
                sub['index'] for sub in ass_subs if sub["language"] == stream_select
            )

    selected_subs = next(
        sub for sub in ass_subs if int(sub["index"]) == int(selected_subs)
    )
    ass_track_path = Path(os.path.join(save_loc, selected_subs["save_file"]))

    # MKVextract subtitle track
    mkv_subs = ["mkvextract", "tracks", input_file_str] + ["2:" + str(ass_track_path)]
    mkv_subs_output = sp.check_output(mkv_subs)

    # To export fonts
    FF = FontFinder()

    # Get font names
    available_fonts = FF.fonts

    if attachments:
        font_files, font_files_extract = export_fonts_list(attachments, save_loc)

        # MKVextract attachments
        mkv_attachments = [
            "mkvextract",
            "attachments",
            input_file_str,
        ] + font_files_extract
        mkv_attachments_output = sp.check_output(mkv_attachments)

        # Get current fonts
        font_names = [FF.font_info_by_file(el) for el in font_files]

        return (
            [selected_subs["save_file"], ass_track_path, available_fonts],
            [font_files, font_names],
        )

    return [selected_subs["save_file"], ass_track_path, available_fonts], []


def subs_mimetype(codec_id):
    if codec_id.lower() == "s_text/ass":
        return ".ass"
    elif codec_id.lower() == "text/plain":
        return ".srt"
    else:
        raise Exception(f"Invalid codec `{codec_id}`")


def export_fonts_list(attachments, save_loc):
    font_files = []
    font_files_extract = []
    for el in attachments:
        fl = os.path.join(save_loc, el["file_name"])
        font_files_extract.append("{}:{}".format(el["id"], fl))

    return font_files, font_files_extract


def cwd():
    """
    Get current working directory.

    Returns
    -------
    Path
    """

    return Path(__file__).cwd()


def main():
    # Input arguments
    user_args = cli_args()

    for x, b in user_args.items():
        mp = []
        for y, fl in enumerate(b["input"]):
            # Check if first/last item for reporting
            if fl == b["input"][0]:
                m = 0
            elif fl == b["input"][-1]:
                m = 1
            else:
                m = None

            # Prepare attachments folder path
            fl_attachments_folder = Path(str(fl.with_suffix("")) + "_attachments")

            # Create attachments directory
            fl_attachments_folder.mkdir(parents=True, exist_ok=True)

            # Extract subs + fonts
            ass, fonts = extract_subsnfonts(
                fl, fl_attachments_folder, b['subtitle_stream_select'][y]
            )

            # Read subs
            lines = read_subs(ass[1])

            # Get Resolution/Format/Styles/Dialogues indices
            ass_ress = {
                "ResX": get_lines_per_type(lines, ["PlayResX: "])[0],
                "ResY": get_lines_per_type(lines, ["PlayResY: "])[0],
            }
            format_lines = get_lines_per_type(lines, ["Format: "])
            style_lines = get_lines_per_type(lines, ["Style: "])
            dialogue_lines = get_lines_per_type(lines, ["Dialogue: ", "Comment: "])

            # Style names
            style_names = [(i, el[0], el[1][0]) for i, el in enumerate(style_lines)]

            # Style names from dialogue
            style_names_dialogue = list(set([el[1][3] for el in dialogue_lines]))

            # Keep the following styles which are in both defined in dialogue and styles
            keep_style_names = set(style_names_dialogue) - set(style_names)

            # Find them back in styles
            keep_style_lines_idx = [
                el[0] for el in style_names if el[2] in keep_style_names
            ]
            remove_style_lines_idx = [
                el[0] for el in style_names if el[2] not in keep_style_names
            ]

            # Kept styles used for restyling
            style_lines_kept = list(itemgetter(*keep_style_lines_idx)(style_lines))

            # User styling settings
            sub_settings = b["subtitle_preset"]

            ffprobe_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v",
                "-show_entries",
                "stream={}".format(",".join(["width", "height"])),
                "-of",
                "json",
                str(fl),
            ]

            # Get video dimensions
            cprocess = sp.run(ffprobe_cmd, capture_output=True)

            # Json output
            ffdims = json.loads(cprocess.stdout)["streams"][0]

            # Resample ; TODO
            # print(ass_ress, sub_settings, vid_dims)


if __name__ == "__main__":
    """ Main """

    # CWD
    wdir = cwd()

    # Attachments folder gene

    # Stop execution at keyboard input
    try:
        resl = main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        pass
