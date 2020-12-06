# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 23:03:08 2020

@author: ToshY

FFconv - Hardcoding MKV to MP4 with FFmpeg

# Example
python ffconv.py -i "./input/" -o "./output/" -e "mp4"
"""

import sys
import re
import argparse
import mimetypes
import json
import pyfiglet
import subprocess as sp
import functools as fc
import collections
import math
from pathlib import Path
from src.simulate import SimulateLoading
from src.colours import TextColours as tc
from rich import print
from rich.prompt import IntPrompt
from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)


class DirCheck(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        all_values = []
        for fl in values:
            p = Path(fl).resolve()
            if not self.const:
                if p.suffix:
                    if not p.parent.is_dir():
                        raise FileNotFoundError(
                            f"[red]The parent directory `{str(p.parent)}` "
                            "for output argument `{str(p)}` does not exist.[/red]"
                        )
                    else:
                        all_values.append({p: "file"})
                else:
                    if not p.is_dir():
                        p.mkdir()
                    all_values.append({p: "directory"})
            else:
                if not p.exists():
                    raise FileNotFoundError(
                        f"[red]The specificed path `{fl}` does not exist.[/red]"
                    )
                if p.is_file():
                    all_values.append({p: "file"})
                else:
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
                f"[red]The specificed output extension `{stripped_ext}` "
                "is not a valid video extension.[/red]"
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
        const=True,
        nargs="+",
        help="Path to input file or directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        action=DirCheck,
        const=False,
        nargs="+",
        help="Path to output directory",
    )
    parser.add_argument(
        "-e",
        "--extension",
        type=str,
        required=True,
        action=ExtCheck,
        help="Extension for the output files",
    )
    parser.add_argument(
        "-vp",
        "--video_preset",
        type=str,
        required=False,
        action=DirCheck,
        nargs="+",
        help="Path to JSON file with FFmpeg video preset options",
    )
    parser.add_argument(
        "-va",
        "--audio_preset",
        type=str,
        required=False,
        action=DirCheck,
        nargs="+",
        help="Path to JSON file with FFmpeg audio preset options",
    )
    args = parser.parse_args()

    # Check args count
    user_args = check_args(
        args.input, args.output, args.video_preset, args.audio_preset
    )

    return user_args, args.input, args.extension


def check_args(inputs, outputs, vpresets, apresets):
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
                f"[red]Amount of input arguments ({len_inputs}) "
                 "does not equal the amount of output arguments ({len_outputs})."
            )

    if vpresets is not None:
        len_vpresets = len(vpresets)
        if len_vpresets != 1:
            if len_inputs != len_vpresets:
                raise Exception(
                    f"[red]Amount of input arguments ({len_inputs}) "
                     "does not equal the amount of video preset arguments ({len_vpresets})."
                )

            vdata = []
            for vp in vpresets:
                vdata.append(
                    dict_to_list(
                        remove_empty_dict_values(read_json(list(vp.keys())[0]))
                    )
                )

        else:
            vdata = dict_to_list(remove_empty_dict_values(read_json(*vpresets[0])))
    else:
        len_vpresets = 0
        vdata = [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-preset",
            "slow",
            "-profile:v",
            "high",
            "-level:v",
            "4.0",
        ]

    if apresets is not None:
        len_apresets = len(apresets)
        if len_apresets != 1:
            if len_inputs != len_apresets:
                raise Exception(
                    f"[red]Amount of input arguments ({len_inputs}) "
                     "does not equal the amount of video preset arguments ({len_apresets})."
                )

            adata = []
            for ap in apresets:
                adata.append(
                    dict_to_list(
                        remove_empty_dict_values(read_json(list(ap.keys())[0]))
                    )
                )
        else:
            adata = dict_to_list(remove_empty_dict_values(read_json(*apresets[0])))
    else:
        len_apresets = 0
        adata = ["-c:a", "aac", "-strict", "2", "-ab", "192k", "-ac", "2"]

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
                        f"[red]The path [cyan]`{str(cpath)}`[/cyan] [red]contains "
                        f"[cyan]`{len_all_files_in_batch}`[/cyan] [red]files but only "
                        f"[cyan]`{len_outputs}`[/cyan] "
                        f"[red]output filename(s) was/were specified.[/red]"
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

        if len_vpresets == 1:
            video_data = vdata
            if ptype == "directory":
                video_data = [video_data for x in range(len(all_files))]
        else:
            if len_vpresets == 0:
                video_data = vdata
                video_data = [video_data for x in range(len(all_files))]
            else:
                video_data = vdata[0]
                vdata.pop(0)
                if ptype == "directory":
                    video_data = [video_data for x in range(len(all_files))]

        if len_apresets == 1:
            audio_data = adata
            if ptype == "directory":
                audio_data = [audio_data for x in range(len(all_files))]
        else:
            if len_apresets == 0:
                audio_data = adata
                audio_data = [audio_data for x in range(len(all_files))]
            else:
                audio_data = adata[0]
                adata.pop(0)
                if ptype == "directory":
                    audio_data = [audio_data for x in range(len(all_files))]

        batch[str(i)] = {
            "input": all_files,
            "output": output_files,
            "video_preset": video_data,
            "audio_preset": audio_data,
        }

    return batch


def print_streams_options(tracks):

    table = Table(show_header=True, header_style="bold cyan")

    # Header
    for key in tracks[0].keys():
        table.add_column(key.capitalize())

    # Rows
    for track in tracks:
        table.add_row(*[str(val) for val in list(track.values())])

    console = Console()
    console.print(table)


def check_streams_order(ffprobe_result):
    """
    Check if stream types are ordered properly.

    Parameters
    ----------
    probe_result : dict
        FFprobe results.

    Raises
    ------
    Exception
        Exception for stream order inconsistencies.

    Returns
    -------
    None.

    """
    # Total streams
    tcount = list(range(0, sum([st["count"] for ix, st in ffprobe_result.items()])))
    # Check count and properly formatted file
    for ty, st in ffprobe_result.items():
        sc = st["count"]
        if tcount[:sc] != [cs["id"] for cs in st["streams"]]:
            raise Exception(
                f"[red]The stream orders are not standarized. Please run [cyan]`mkvremux.py`[red] to sort the streams automatically with appropriate ordering.[/red]"
            )

        del tcount[:sc]


def check_streams_count(ffprobe_result):
    """
    Check the stream type count.

    Parameters
    ----------
    probe_result : list
        List of dicts of video, audio and subtitle streams.

    Raises
    ------
    Exception
        Raises exception when the file does not contain necessary video, audio and subtitle tracks.

    Returns
    -------
    None.

    """
    for t, st in ffprobe_result.items():
        if st["count"] < 1:
            raise Exception(
                f"[red]The file did not contain necessary stream type `{t}`. "
                "File needs atleast 1 video (`v`), 1 audio (`a`) "
                "and 1 subtitle (`s`) stream.[/red]"
            )


def stream_user_input(ffprobe_result):
    """
    Get stream mapping and possible user input in case of multiple streams for specific type.

    Parameters
    ----------
    probe_result : list
        List of dicts of video, audio and subtitle streams.

    Raises
    ------
    Exception
        Raises exception if stream count is 0.

    Returns
    -------
    stream_map : dict
        A key-value pair of stream type and mapping id.

    """

    stream_map = {}
    stream_sum_count = 0
    for ty, st in ffprobe_result.items():
        if st["count"] == 0:
            raise Exception(
                f"[red]No streams for type `{ty}` found. "
                "Please make sure there's atleast 1 video, 1 audio and "
                "1 subtitle stream.[/red]"
            )

        if st["count"] == 1:
            stream_map[ty] = st["streams"][0]["id"]
        else:
            print(f"\r\n> Multiple [cyan]{ty}[/cyan] streams detected")

            # Default
            selected_stream = st["streams"][0]["id"]

            # Stream properties
            stream_properties = [
                {
                    "id": cs["id"],
                    "codec": cs["properties"]["codec_id"],
                    "language": (cs["properties"]["language"] if cs["properties"] is not None else ''),
                    "title": (cs["properties"]["track_name"] if cs["properties"] is not None else ''),
                }
                for cs in st["streams"]
            ]

            print_streams_options(stream_properties)
            allowed = [str(cs["id"]) for cs in stream_properties]

            # Request user input
            selected_stream = IntPrompt.ask(
                "\r\n# Please specify the subtitle id to use: ",
                choices=allowed,
                default=selected_stream,
                show_choices=True,
                show_default=True,
            )
            print(f"\r> Stream index [green]`{selected_stream}`[/green] selected!")

            stream_map[ty] = selected_stream

        # print(ty, stream_sum_count, st["count"])

        # Remap subtitle due to filter complex
        if ty != "subtitles":
            stream_sum_count = stream_sum_count + st["count"]
        else:
            stream_map[ty] = int(stream_map[ty]) - stream_sum_count

    return stream_map


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


def split_list_of_dicts_by_key(list_of_dicts, key="codec_type"):
    """
    Split list of dictonaries by specified key

    Parameters
    ----------
    list_of_dicts : list
        List of dictonaries.
    key : string, optional
        The key to split the list of dictonaries on. The default is 'codec_type'.

    Returns
    -------
    result_list : list
        List of dictonaries splitted by key.

    """

    result = collections.defaultdict(list)
    keys = []
    for d in list_of_dicts:
        result[d[key]].append(d)
        if d[key] not in keys:
            keys.append(d[key])

    result_list = list(result.values())

    streams = {k: {"streams": {}, "count": 0} for k in keys}
    for x, s in enumerate(streams):
        streams[s]["streams"] = result_list[x]
        streams[s]["count"] = len(streams[s]["streams"])
        # for st in streams[s]['streams']:
        #     if 'properties' in st:
        #         if 'codec_private_data' in st['properties']:
        #             st['properties'].pop('codec_private_data', None)

    return streams


def probe_file(
    input_file, idx, original_batch, mark, extra_tags=["track_name", "language"]
):
    """
    FFprobe to get video/audio/subtitle streams.

    Parameters
    ----------
    input_file : Path
        The specified input file as Path object.

    Raises
    ------
    Exception
        Raised if exit code from FFprobe is not 0.

    Returns
    -------
    probe_output : dict
        Dictonary with tracks of the video/audio/subtitle streams.

    """

    original_batch_name = str([*original_batch][0])

    if mark == 0:
        print(f"\r\n\r\n> FFprobe batch for [cyan]`{original_batch_name}`[/cyan]")

    # Regex
    main_tags = ["id", "codec_name"]

    print(f"> Starting FFprobe for [cyan]`{input_file.name}`[/cyan]")
    # Probe; changed to MKVmerge idenitfy due to FFprobe identifying cover pictures as video streams
    mkvidentify_cmd = [
        "mkvmerge",
        "--identify",
        "--identification-format",
        "json",
        str(input_file),
    ]
    mkvidentify_process = sp.run(mkvidentify_cmd, capture_output=True)

    # Json output
    mkvidentify_out = json.loads(mkvidentify_process.stdout)

    # Split by codec_type
    streams = split_list_of_dicts_by_key(mkvidentify_out["tracks"], "type")

    # Check if file has consistent streams
    check_streams_order(streams)

    mapping = None
    # Check if first file from batch for mapping in converison later
    if idx == 0:
        mapping = stream_user_input(streams)

    print("\r\n\r\n> FFprobe complete")

    if mark == 1:
        print(f"\r\n> FFprobe batch complete for [cyan]`{original_batch_name}`[/cyan]")

    return streams, mapping


def convert_file(
    input_file,
    output_dir,
    output_ext,
    mapping,
    video_preset_data,
    audio_preset_data,
    original_batch,
    mark,
):
    """
    FFmpeg file conversion with specified preset options

    Parameters
    ----------
    input_file : Path
        The specified input file as Path object.

    Raises
    ------
    Exception
        Raised if exit code from FFprobe is not 0.

    Returns
    -------
    probe_output : dict
        Dictonary with tracks of the video/audio/subtitle streams.

    """

    original_batch_name = str([*original_batch][0])

    if mark == 0:
        print(f"\r\n\r\n> FFmpeg batch for [cyan]`{original_batch_name}`[/cyan]")

    # Get file duration first
    ffprobe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(input_file),
    ]
    ffprobe_process = sp.run(ffprobe_cmd, capture_output=True)
    file_duration = float(ffprobe_process.stdout)

    # Preset data
    v_data = video_preset_data
    a_data = audio_preset_data

    # Output split
    output_path = list(output_dir.keys())[0]
    output_type = list(output_dir.values())[0]

    # Output extension
    output_ext_formatted = "." + output_ext["extension"].lstrip(".")

    # Prepare output file name
    if output_type == "directory":
        output_file = str(output_path.joinpath(input_file.stem + output_ext_formatted))
    else:
        output_file = str(output_path.with_suffix("").with_suffix(output_ext_formatted))

    # Prepare mapping data
    v_map = "0:" + str(mapping["video"])
    a_map = "0:" + str(mapping["audio"])

    # Filter complex subtitle map requires this escaped monstrosity (for Windows atleast)
    lit_file = str(input_file).replace("\\", "\\\\").replace(":", "\:")
    s_map = "subtitles='" + lit_file + "':si=" + str(mapping["subtitles"])

    # FFmpeg command
    ffmpeg_cmd = (
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_file),
            "-metadata",
            "title=" + input_file.stem,
            "-map",
            v_map,
            "-map",
            a_map,
            "-filter_complex",
            s_map,
        ]
        + v_data
        + a_data
        + ["-movflags", "faststart", "-progress", "-", output_file]
    )

    print("\r\n> The following FFmpeg will be executed:\r\n")
    print(f"[green]{' '.join(ffmpeg_cmd)}[/green]\r\n")

    # Start conversion
    with Progress(
        "[progress.description]{task.description}",
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Converting...", total=math.ceil(file_duration))
        while not progress.finished:
            process = sp.Popen(
                ffmpeg_cmd, stdout=sp.PIPE, stderr=sp.STDOUT, universal_newlines=True
            )
            prev = [0]
            rmbr = 5
            for x, line in enumerate(process.stdout):
                if x == rmbr:
                    cdur = round(int(re.search(r"\d+", line).group()) / 1e6)
                    adv = cdur - prev[-1]
                    prev.append(cdur)
                    progress.update(task, advance=adv)
                    rmbr += 11

        progress.update(task, description="[cyan]Conversion complete!")

    return_code = process.wait()
    if return_code != 0:
        raise Exception(f"[red]FFmpeg returned exit code `{return_code}`.[/red]")

    if mark == 1:
        print(f"\r\n> FFmpeg batch complete for [cyan]`{original_batch_name}`[/cyan]")

    return None


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
    user_args, original_input, extension = cli_args()

    # FFprobe
    for x, b in user_args.items():
        bn = []
        mp = []
        for y, fl in enumerate(b["input"]):
            # Check if first/last item for reporting
            if fl == b["input"][0]:
                m = 0
            elif fl == b["input"][-1]:
                m = 1
            else:
                m = None

            if y == 0:
                probe_result, mapping = probe_file(fl, y, original_input[int(x)], m)
            else:
                probe_result, _ = probe_file(fl, y, original_input[int(x)], m)

            # Check if probe contains atleast 1 v/a/s stream
            check_streams_count(probe_result)

            # Append mapping
            mp.append(mapping)

            # First in batch
            bn.append(m)

        b["nr_in_batch"] = bn
        b["stream_mapping"] = mp

    # FFmpeg
    for x, b in user_args.items():
        for z, flc in enumerate(b["input"]):
            # Check if first/last item for reporting
            convert_file(
                flc,
                b["output"][z],
                extension,
                b["stream_mapping"][z],
                b["video_preset"][z],
                b["audio_preset"][z],
                original_input[int(x)],
                b["nr_in_batch"][z],
            )

    return user_args.items()


if __name__ == "__main__":
    """ Main """

    # CWD
    wdir = cwd()

    # Stop execution at keyboard input
    try:
        batches = main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        pass
