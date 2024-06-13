# -*- coding: utf-8 -*-

import argparse
import json
import re
import subprocess as sp
from datetime import datetime
from pathlib import Path
from src.banner import cli_banner
from src.table import table_print_stream_options
from src.args import FileDirectoryCheck, ExtensionCheck, files_in_dir
from src.general import (
    read_json,
    remove_empty_dict_values,
    dict_to_list,
    list_to_dict,
    split_list_of_dicts_by_key,
)
from rich import print
from rich.prompt import IntPrompt
from src.logger import Logger, ProcessDisplay
from loguru import logger


def cli_args(args=None):
    """
    Command Line argument parser.

    Returns
    -------
    str
        The path of the input file/directory.
    str
        The path of the output directory.
    tuple
        The tuple to sort on key for each track in the accompanied stream.

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
        required=False,
        action=ExtensionCheck,
        help="Extension for the output files",
        default={"extension": "mp4"},
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
    parser.add_argument(
        "-fc",
        "--filter_complex",
        type=str,
        required=False,
        action=FileDirectoryCheck,
        nargs="+",
        help="Path to JSON file with FFmpeg preset options for additional filter complex",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Verbose logging",
    )

    if args is not None:
        args = parser.parse_args(args)
    else:
        args = parser.parse_args()

    # Check args
    user_args = check_args(
        args.input,
        args.output,
        args.video_preset,
        args.audio_preset,
        args.filter_complex
    )

    return user_args, args.input, args.extension, args.verbose


def check_args(inputs, outputs, vpresets, apresets, fcpresets):
    """
    Check the amount of input arguments, outputs and presets.

    Parameters
    ----------
    inputs : list
        Input argument(s).
    outputs : list
        Output argument(s).
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
                f"does not equal the amount of output arguments ({len_outputs})."
            )

    if vpresets is not None:
        len_vpresets = len(vpresets)
        if len_vpresets != 1:
            if len_inputs != len_vpresets:
                raise Exception(
                    f"Amount of input arguments ({len_inputs}) "
                    f"does not equal the amount of video preset arguments ({len_vpresets})."
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
                    f"Amount of input arguments ({len_inputs}) "
                    f"does not equal the amount of audio preset arguments ({len_apresets})."
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

    if fcpresets is not None:
        len_fcpresets = len(fcpresets)
        if len_fcpresets != 1:
            if len_inputs != len_fcpresets:
                raise Exception(
                    f"Amount of input arguments ({len_inputs}) "
                    f"does not equal the amount of filter complex preset arguments ({len_fcpresets})."
                )

            fcdata = []
            for ap in fcpresets:
                fcdata.append(
                    dict_to_list(
                        remove_empty_dict_values(read_json(list(ap.keys())[0]))
                    )
                )
        else:
            fcdata = dict_to_list(remove_empty_dict_values(read_json(*fcpresets[0])))
    else:
        len_fcpresets = 0
        fcdata = ["before", "", "after", ""]

    # Prepare inputs/outputs/presets
    batch = {}
    for i, el in enumerate(inputs):

        cpath = [*el][0]
        ptype = str(*el.values())

        all_files = []
        if ptype == "file":
            all_files = [Path(cpath)]
        elif ptype == "directory":
            all_files = files_in_dir(cpath)

        # Replace single/double quotes in filenames for FFmpeg
        for cf, current_file_path in enumerate(all_files):
            # Replace single or double quotes in filename needed for FFmpeg
            new_filename = re.sub(r"[\"']", "", current_file_path.name)
            new_file_path = current_file_path.with_name(new_filename)
            current_file_path.rename(new_file_path)

            all_files[cf] = new_file_path

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
                    output_files = [outputs[0] for _ in range(len(all_files))]
        else:
            output_files = outputs[0]
            # Unset
            outputs.pop(0)
            # Check type
            if ptype == "directory":
                # Create copies
                output_files = [output_files for _ in range(len(all_files))]

        if len_vpresets == 1:
            video_data = vdata
            if ptype == "directory":
                video_data = [video_data for _ in range(len(all_files))]
        else:
            if len_vpresets == 0:
                video_data = vdata
                video_data = [video_data for _ in range(len(all_files))]
            else:
                video_data = vdata[0]
                vdata.pop(0)
                if ptype == "directory":
                    video_data = [video_data for _ in range(len(all_files))]

        if len_apresets == 1:
            audio_data = adata
            if ptype == "directory":
                audio_data = [audio_data for _ in range(len(all_files))]
        else:
            if len_apresets == 0:
                audio_data = adata
                audio_data = [audio_data for _ in range(len(all_files))]
            else:
                audio_data = adata[0]
                adata.pop(0)
                if ptype == "directory":
                    audio_data = [audio_data for _ in range(len(all_files))]

        if len_fcpresets == 1:
            filter_complex_data = fcdata
            if ptype == "directory":
                filter_complex_data = [filter_complex_data for _ in range(len(all_files))]
        else:
            if len_fcpresets == 0:
                filter_complex_data = fcdata
                filter_complex_data = [filter_complex_data for _ in range(len(all_files))]
            else:
                filter_complex_data = fcdata[0]
                fcdata.pop(0)
                if ptype == "directory":
                    filter_complex_data = [filter_complex_data for _ in range(len(all_files))]

        batch[str(i)] = {
            "input": all_files,
            "output": output_files,
            "video_preset": video_data,
            "audio_preset": audio_data,
            "filter_complex_preset": filter_complex_data
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
                "The stream orders are not standardized. "
                "Please run `mkvremux.py` to sort the streams "
                "automatically with appropriate ordering."
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
                f"File needs at least 1 video (`v`), 1 audio (`a`) "
                f"and 1 subtitle (`s`) stream.[/red]"
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
                f"Please make sure there's at least 1 video, 1 audio and "
                f"1 subtitle stream.[/red]"
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
                        else "n/a"
                    ),
                    "title": (
                        cs["properties"]["track_name"]
                        if "track_name" in cs["properties"]
                        else "n/a"
                    ),
                    "default":         (
                        cs["properties"]["default_track"]
                        if "default_track" in cs["properties"]
                        else "n/a"
                    ),
                }
                for cs in st["streams"]
            ]

            table_print_stream_options(stream_properties)
            allowed = [str(cs["id"]) for cs in stream_properties]

            # Request user input
            selected_stream = IntPrompt.ask(
                f"\r\n# Please specify the {ty} id to use: ",
                choices=allowed,
                default=selected_stream,
                show_choices=True,
                show_default=True,
            )
            print(f"\r> Stream index [green]`{selected_stream}`[/green] selected!")

            stream_map[ty] = selected_stream

        # Remap subtitle due to filter complex
        if ty != "subtitles":
            stream_sum_count = stream_sum_count + st["count"]
        else:
            stream_map[ty] = int(stream_map[ty]) - stream_sum_count

    return stream_map


def probe_file(input_file, idx, original_batch, mark):
    """
    MKVidentify to get video/audio/subtitle streams.

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
        Dictionary with tracks of the video/audio/subtitle streams.

    """

    original_batch_name = str([*original_batch][0])

    if mark == 0:
        print(f"\r\n\r\n> MKVidentify batch for [cyan]`{original_batch_name}`[/cyan]")

    print(f"\r\n> Starting MKVidentify for [cyan]`{input_file.name}`[/cyan]")

    mkvidentify_cmd = [
        "mkvmerge",
        "--identify",
        "--identification-format",
        "json",
        str(input_file),
    ]

    process = ProcessDisplay(logger)
    result = process.run("MKVmerge identify", mkvidentify_cmd)

    # Json output
    mkvidentify_out = json.loads(result.stdout)
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
    for x, s in enumerate(split_keys):
        streams[s]["streams"] = split_streams[x]
        streams[s]["count"] = len(streams[s]["streams"])

    # Check if file has consistent streams
    check_streams_order(streams)

    mapping = None
    # Check if first file from batch for mapping in conversion later
    if idx == 0:
        mapping = stream_user_input(streams)

    print("> MKVidentify [green]completed[/green]!")

    if mark == 1:
        print(
            f"\r\n> MKVidentify batch completed for [cyan]`{original_batch_name}`[/cyan]\r\n"
        )

    return streams, mapping


def convert_file(
        input_file,
        output_dir,
        output_ext,
        mapping,
        video_preset_data,
        audio_preset_data,
        filter_complex_preset_data,
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
        Dictionary with tracks of the video/audio/subtitle streams.

    """

    original_batch_name = str([*original_batch][0])

    if mark == 0:
        print(f"\r\n\r\n> FFmpeg batch for [cyan]`{original_batch_name}`[/cyan]")

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
    filter_complex_map = ("subtitles='" + lit_file + "':si=" + str(mapping["subtitles"]),)

    # Additional filter complex; added due to possible issues when subtitles use BT.709 color space.
    filter_complex_data_before = filter_complex_preset_data.get("before", "")
    if len(filter_complex_data_before.strip()):
        filter_complex_map = (filter_complex_data_before.strip().rstrip(","), *filter_complex_map)

    filter_complex_data_after = filter_complex_preset_data.get("after", "")
    if len(filter_complex_data_after.strip()):
        filter_complex_map = (*filter_complex_map, filter_complex_data_after.strip().lstrip(","))

    filter_complex_map_concat = ",".join(filter_complex_map)
    filter_complex_map_complete = f"[{v_map}]{filter_complex_map_concat}"

    current_datetime = datetime.now()

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
                "-metadata",
                f'comment=Encoded on {current_datetime.strftime("%Y-%m-%d %H:%M:%S")}',
                "-map",
                a_map,
                "-filter_complex",
                filter_complex_map_complete,
            ]
            + v_data
            + a_data
            + ["-movflags", "faststart", output_file]
    )

    process = ProcessDisplay(logger)
    result = process.run("FFmpeg convert", ffmpeg_cmd)

    if mark == 1:
        print(f"\r\n> FFmpeg batch complete for [cyan]`{original_batch_name}`[/cyan]")

    return None


@logger.catch
def main(custom_args=None):
    # Input arguments
    user_args, original_input, extension, verbose = cli_args(custom_args)

    # Logger
    global logger
    logger = Logger(Path(__file__).stem, verbose).logger

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

            # Rename input filename in case it contains single or double quotes

            if y == 0:
                probe_result, mapping = probe_file(fl, y, original_input[int(x)], m)
            else:
                probe_result, _ = probe_file(fl, y, original_input[int(x)], m)

            # Check if probe contains at least 1 v/a/s stream
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
            output = b["output"]
            video_preset = b["video_preset"]
            audio_preset = b["audio_preset"]
            filter_complex = b["filter_complex_preset"]

            # If input was directory use the index
            if type(output) is list:
                output = output[z]
                video_preset = video_preset[z]
                audio_preset = audio_preset[z]
                filter_complex = filter_complex[z]

            # Check if first/last item for reporting
            convert_file(
                flc,
                output,
                extension,
                b["stream_mapping"][z],
                video_preset,
                audio_preset,
                list_to_dict(filter_complex),
                original_input[int(x)],
                b["nr_in_batch"][z],
            )

    return user_args.items()


if __name__ == "__main__":
    """ Main """
    cli_banner(__file__)

    # Stop execution at keyboard input
    try:
        main_result = main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        exit()
