# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 23:03:08 2020

@author: ToshY

FFconv - Hardcoding MKV to MP4 with FFmpeg

# Example
python ffconv.py -i "./input/" -o "./output/" -e "mp4"
"""

import argparse
import json
import subprocess as sp
from pathlib import Path
from src.banner import cli_banner
from src.table import table_print_stream_options
from src.args import FileDirectoryCheck, ExtensionCheck, files_in_dir
from src.general import (
    read_json,
    remove_empty_dict_values,
    dict_to_list,
    split_list_of_dicts_by_key,
)
from rich import print
from rich.prompt import IntPrompt


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

    # Arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        action=FileDirectoryCheck,
        const=True,
        nargs="+",
        help="Path to input file or directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        action=FileDirectoryCheck,
        const=False,
        nargs="+",
        help="Path to output directory",
    )
    parser.add_argument(
        "-e",
        "--extension",
        type=str,
        required=True,
        action=ExtensionCheck,
        help="Extension for the output files",
    )
    parser.add_argument(
        "-vp",
        "--video_preset",
        type=str,
        required=False,
        action=FileDirectoryCheck,
        nargs="+",
        help="Path to JSON file with FFmpeg video preset options",
    )
    parser.add_argument(
        "-ap",
        "--audio_preset",
        type=str,
        required=False,
        action=FileDirectoryCheck,
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
                    "language": (
                        cs["properties"]["language"]
                        if "language" in cs["properties"]
                        else ""
                    ),
                    "title": (
                        cs["properties"]["track_name"]
                        if "track_name" in cs["properties"]
                        else ""
                    ),
                }
                for cs in st["streams"]
            ]

            table_print_stream_options(stream_properties)
            allowed = [str(cs["id"]) for cs in stream_properties]

            # Request user input
            selected_stream = IntPrompt.ask(
                "\r\n# Please specify the {ty} id to use: ",
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
        print(f"\r\n\r\n> MKVidentify batch for [cyan]`{original_batch_name}`[/cyan]")

    # Regex
    main_tags = ["id", "codec_name"]

    print(f"\r\n> Starting MKVidentify for [cyan]`{input_file.name}`[/cyan]")
    # Changed to MKVmerge identify due to FFprobe identifying cover pictures as video streams
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
    if mkvidentify_out["errors"]:
        raise Exception(
            'MKVidentify encountered the following error: "{}"'.format(
                mkvidentify_out["errors"][0]
            )
        )

    # Split by codec_type
    split_streams, split_keys = split_list_of_dicts_by_key(
        mkvidentify_out["tracks"], "type"
    )

    # Rebuild streams & count per codec type
    streams = {k: {"streams": {}, "count": 0} for k in split_keys}
    for x, s in enumerate(split_streams):
        streams[s]["streams"] = split_streams[x]
        streams[s]["count"] = len(streams[s]["streams"])

    # Check if file has consistent streams
    check_streams_order(streams)

    mapping = None
    # Check if first file from batch for mapping in converison later
    if idx == 0:
        mapping = stream_user_input(streams)

    print("> MKVidentify [green]completed[/green]!")

    if mark == 1:
        print(f"\r\n> MKVidentify batch completed for [cyan]`{original_batch_name}`[/cyan]\r\n")

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
        + ["-movflags", "faststart", output_file]
    )

    print("> The following FFmpeg command will be executed:\r\n")
    print(f"[green]{' '.join(ffmpeg_cmd)}[/green]")

    print(f"\r\n> FFmpeg conversion [cyan]running...[/cyan]", end="\r")
    cprocess = sp.run(ffmpeg_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    return_code = cprocess.returncode
    print("> FFmpeg conversion [green]completed[/green]!\r\n")

    if return_code != 0:
        raise Exception(f"[red]FFmpeg returned exit code `{return_code}`.[/red]")

    if mark == 1:
        print(f"\r\n> FFmpeg batch complete for [cyan]`{original_batch_name}`[/cyan]")

    return None


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
    cli_banner(__file__)

    # Stop execution at keyboard input
    try:
        batches = main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        pass
