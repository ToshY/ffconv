# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 23:03:08 2020

@author: ToshY

MKVremux - Remuxing MKV files to appropriate stream ordering

# Example
python mkvremux.py -i "input/file.mkv" -o "output" -s "preset/sort_preset.json"
"""

import json
import numpy as np
import argparse
import subprocess as sp
from pathlib import Path
from src.banner import cli_banner
from src.args import FileDirectoryCheck, files_in_dir
from src.general import (
    find_in_dict,
    read_json,
    remove_empty_dict_values,
    dict_to_list,
    dict_to_tuple,
    split_list_of_dicts_by_key,
)
from rich import print
from rich.prompt import IntPrompt


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
        "-s",
        "--sort",
        type=str,
        required=False,
        nargs="+",
        help="Sorting tags",
    )

    args = parser.parse_args()
    user_args = check_args(args.input, args.output, args.sort)

    return user_args, args.input


def check_args(inputs, outputs, sorts):
    """
    Check the amount of input arguments, outputs and presets.

    Parameters
    ----------
    inputs : list
        Input argument(s).
    outputs : list
        Output arugment(s).
    sorts : list
        Video preset argument(s).

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

    if sorts is not None:
        len_sorts = len(sorts)
        if len_sorts != 1:
            if len_inputs != len_sorts:
                raise Exception(
                    f"Amount of input arguments ({len_inputs}) "
                    "does not equal the amount of sort preset arguments ({len_sorts})."
                )

            sdata = []
            for sp in sorts:
                sdata.append(
                    dict_to_list(
                        remove_empty_dict_values(read_json(list(sp.keys())[0]))
                    )
                )
        else:
            sdata = dict_to_tuple(read_json(sorts[0]))
    else:
        len_sorts = 0
        sdata = [("track_name", False), ("language", False)]

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
                        f"The path `{str(cpath)}` contains "
                        f"`{len_all_files_in_batch}`files but only "
                        f"`{len_outputs}` "
                        f"output filename(s) was/were specified."
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

        if len_sorts == 1:
            sort_data = sdata
            if ptype == "directory":
                sort_data = [sort_data for x in range(len(all_files))]
        else:
            if len_sorts == 0:
                sort_data = sdata
                sort_data = [sort_data for x in range(len(all_files))]
            else:
                sort_data = sdata[0]
                sdata.pop(0)
                if ptype == "directory":
                    sort_data = [sort_data for x in range(len(all_files))]

        batch[str(i)] = {
            "input": all_files,
            "output": output_files,
            "sort_preset": sort_data,
        }

    return batch


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
        Dictonary with tracks of the video/audio/subtitle streams.

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
    for x, s in enumerate(split_keys):
        streams[s]["streams"] = split_streams[x]
        streams[s]["count"] = len(streams[s]["streams"])

    # Sort streams to video - audio - subtitles
    streams = {k: streams[k] for k in ["video", "audio", "subtitles"]}
    print("> MKVidentify [green]completed[/green]!")

    if mark == 1:
        print(
            f"\r\n> MKVidentify batch completed for [cyan]`{original_batch_name}`[/cyan]\r\n"
        )

    return streams


def remux_file(
    input_file,
    track_order,
    output_dir,
    original_batch,
    mark,
    new_file_suffix=" (1)",
):
    """
    Remuxing file with logically resorting of indices to comply with the
    standard ordering of video - audio - subtitle streams.
    Extra priorty can be specified to sort based on codec, language or title.

    Parameters
    ----------
    input_file : Path
        The specified input file as Path object
    track_order : list
        The new correct track ordering
    preferences : tuple, optional
        Option to set sorting by keys. The default is (('title', False)).

    Raises
    ------
    Exception
        Raised if exit code from MKVmerge is not 0

    Returns
    -------
    return_code : TYPE
        The response from the subprocess for the MKVmerge binary

    """

    original_batch_name = str([*original_batch][0])

    if mark == 0:
        print(f"> MKVmerge batch for [cyan]`{original_batch_name}`[/cyan]\r\n")

    track_order_args = ",".join(["0:" + str(v) for v in track_order])

    # Output split
    output_path = list(output_dir.keys())[0]
    output_type = list(output_dir.values())[0]

    # Output extension
    output_extension = ".mkv"

    # Prepare output file name
    if output_type == "directory":
        output_file = str(
            output_path.joinpath(input_file.stem + new_file_suffix + output_extension)
        )
    else:
        output_file = str(output_path.with_suffix("").with_suffix(output_extension))

    input_file_str = str(input_file)
    mkvmerge_cmd = [
        "mkvmerge",
        "--output",
        output_file,
        "(",
        input_file_str,
        ")",
        "--track-order",
        track_order_args,
    ]

    print("> The following MKVmerge command will be executed:\r")
    print(f"[green]{' '.join(mkvmerge_cmd)}[/green]")

    print(f"\r> MKVmerge [cyan]running...[/cyan]", end="\r")
    cprocess = sp.run(mkvmerge_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    return_code = cprocess.returncode
    if return_code != 0:
        raise Exception(f"MKVmerge returned exit code `{return_code}`.")
    print("> MKVmerge [green]completed[/green]!\r\n")

    if mark == 1:
        print(f"> MKVmerge batch complete for [cyan]`{original_batch_name}`[/cyan]")

    return None


def multisort(xs, specs):
    """
    Sort list of dictonaries by (multiple) keys

    Parameters
    ----------
    xs : list
        List with dictonaries to be sorted
    specs : tuple
        Sorting by specified keys with optional reverse


    Returns
    -------
    xs : list
        The sorted input list

    """
    if len(np.shape(specs)) == 1:
        xs.sort(
            key=lambda nx: nx["properties"][specs[0]]
            if specs[0] in nx["properties"]
            else "",
            reverse=specs[1],
        )
    else:
        for key, reverse in reversed(specs):
            xs.sort(
                key=lambda nx: nx["properties"][key] if key in nx["properties"] else "",
                reverse=reverse,
            )
    return xs


def main():
    # Input arguments
    user_args, original_input = cli_args()

    # Batching
    for x, b in user_args.items():
        to = []
        pl = []
        bn = []
        mp = []
        for y, fl in enumerate(b["input"]):
            # Prepare sort
            sort_by_key = b["sort_preset"][y]

            # Check if first/last item for reporting
            if fl == b["input"][0]:
                m = 0
            elif fl == b["input"][-1]:
                m = 1
            else:
                m = None

            probe_result = probe_file(fl, y, original_input[int(x)], m)

            to_redone = []
            for pb in probe_result:
                ps_stream = probe_result[pb]["streams"]

                cstream = []
                for xnl in ps_stream:
                    cstream.append(xnl["id"])

                # Subresort by title, lang, etc...
                opn = multisort(ps_stream, sort_by_key)

                for csi, cse in enumerate(cstream):
                    indx = find_in_dict(input_list=opn, key="id", value=cse)
                    if csi != indx:
                        cstream[csi], cstream[indx] = cstream[indx], cstream[csi]

                to_redone = to_redone + cstream

            # Append batch nr, probe result and new track order
            bn.append(m)
            pl.append(probe_result)
            to.append(to_redone)

        b["nr_in_batch"] = bn
        b["track_order"] = to

    # MKVremux; TODO skip files if already ordered properly (range)
    for x, b in user_args.items():
        for z, flc in enumerate(b["input"]):
            rmx = remux_file(
                flc,
                b["track_order"][z],
                b["output"][z],
                original_input[int(x)],
                b["nr_in_batch"][z],
            )

    return user_args.items()


if __name__ == "__main__":
    """ Main """
    cli_banner(__file__)

    # Stop execution at keyboard input
    try:
        main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        exit()
