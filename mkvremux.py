# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 23:03:08 2020

@author: ToshY

MKVremux - Remuxing MKV files to appropriate stream ordering

# Example
python mkvremux.py -i "./input/file.mkv" -o "./output"
"""

import re
import numpy as np
import argparse
import subprocess as sp
import itertools
from pathlib import Path
from operator import itemgetter
from src.banner import cli_banner
from src.simulate import SimulateLoading
from src.args import FileDirectoryCheck, files_in_dir
from src.general import list_to_dict, find_in_dict


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

    # Banner
    cli_banner()

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
        "-s",
        "--sort",
        type=str,
        required=False,
        nargs="+",
        default=["title"],
        help="Sorting on tags",
    )

    args = parser.parse_args()

    return args.input, args.output, args.sort


def probe_file(input_file, extra_tags=["title"]):
    """
    FFprobe to get video/audio/subtitle streams

    Parameters
    ----------
    input_file : Path
        The specified input file as Path object

    Raises
    ------
    Exception
        Raised if exit code from FFprobe is not 0

    Returns
    -------
    probe_output : dict
        Dictonary with tracks of the video/audio/subtitle streams

    """

    # Regex
    main_tags = ["index", "codec_name"]

    print("\r\n> Starting FFprobe for `{}`".format(input_file.name))
    # Probe
    probe_output = {k: {"streams": {}, "count": 0} for k in ["v", "a", "s"]}
    for s in probe_output:
        cprocess = sp.Popen(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                s,
                "-show_entries",
                "stream={},:stream_tags={}".format(
                    ",".join(main_tags), ",".join(extra_tags)
                ),
                "-of",
                "csv=s=,:nk=0:p=0",
                str(input_file),
            ],
            stdout=sp.PIPE,
            stderr=sp.PIPE,
        )

        # Animate process in terminal
        SL = SimulateLoading(f"FFprobe stream `{s}`")
        return_code = SL.check_probe(cprocess)

        if return_code != 0:
            raise Exception(f"[red]FFprobe returned exit code `{return_code}`.[/red]")

        # Get CSV response
        oprocess = cprocess.communicate()[0].decode("utf-8").splitlines()

        # Split, clean and create dict
        oprocess = [
            list_to_dict(list(filter(None, re.split("([a-z_:]+)=", x))))
            for x in oprocess
        ]

        # Stream tags contain prefix 'tag:'
        extra_tags_prefixed = ["tag:" + el for el in extra_tags]

        stream_output = []
        for ix, ss in enumerate(oprocess):
            # Check if the extra tags are specified, else let them be empty
            for el in main_tags + extra_tags_prefixed:
                if el not in ss:
                    oprocess[ix][el] = ""
                    continue

                oprocess[ix][el] = ss[el].rstrip(",")

            ss["index"] = int(ss["index"])
            stream_output.append(ss)

        probe_output[s]["streams"] = stream_output
        probe_output[s]["count"] = len(probe_output[s]["streams"])

    print("\r\n\r\n> FFprobe complete")
    return input_file.name, probe_output


def remux_file(
    input_file,
    probe_info,
    tracks_to_remove,
    output_dir,
    new_file_suffix=" (1)",
    preferences=(("title", False),),
):
    """
    Remuxing file with logically resorting of indices to comply with the
    standard ordering of video - audio - subtitle streams.
    Extra priorty can be specified to sort based on codec, language or title.

    Parameters
    ----------
    input_file : Path
        The specified input file as Path object
    probe_info : dict
        The corresponding FFprobe info for the input file
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

    fnl_redone = []
    for pb in probe_info:
        ps_stream = probe_info[pb]["streams"]

        cstream = []
        for x in ps_stream:
            cstream.append(x["index"])

        # Subresort by title, lang, etc...
        opn = multisort(ps_stream, preferences)

        for csi, cse in enumerate(cstream):
            indx = find_in_dict(lst=opn, key="index", value=cse)
            if csi != indx:
                cstream[csi], cstream[indx] = cstream[indx], cstream[csi]

        fnl_redone = fnl_redone + cstream

    # Remove inconsistent tracks
    mkv_cmd_add = []
    if tracks_to_remove is not None:
        print("\r\n\r\n> The tracks with the following IDs will be removed:\r\n")
        print(tracks_to_remove)
        ### ! FIX THIS, -A track_ids should be stream specific
        fnl_redone = [e for e in fnl_redone if e not in tracks_to_remove]
        for el in tracks_to_remove:
            if el == "v":
                vl = "video"
            elif el == "a":
                vl = "audio"
            elif el == "s":
                vl = "subtitle"

            fnl_redone = [e for e in fnl_redone if e not in tracks_to_remove[el]]
            mkv_cmd_add.append(
                [
                    "--" + vl + "-tracks",
                    "!" + ",".join([str(v) for v in tracks_to_remove[el]]),
                ]
            )

        mkv_cmd_add = list(itertools.chain(*mkv_cmd_add))

    track_order_args = ",".join(["0:" + str(v) for v in fnl_redone])

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
    mkv_cmd = (
        ["mkvmerge", "--output", output_file]
        + mkv_cmd_add
        + ["(", input_file_str, ")", "--track-order", track_order_args]
    )

    mkv_cmd_verbose = " ".join(mkv_cmd)
    print("\r\n\r\n> The following MKVmerge command will be executed:\r\n")
    print(mkv_cmd_verbose)

    try:
        cprocess = sp.Popen(mkv_cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        # Animate process in terminal
        SL = SimulateLoading("Remuxing")
        return_code = SL.check_probe(cprocess)

        if return_code != 0:
            raise Exception(
                "[red]MKVmerge returned exit code [cyan]{}[/cyan][/red].".format(
                    return_code
                )
            )

        return return_code
    except Exception as e:
        raise (
            "[red]An error occured while trying to remux your file:[/red]\n\r[cyan]{}[/cyan]".format(
                e.output.decode("utf-8")
            )
        )


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
        xs.sort(key=itemgetter(specs[0]), reverse=specs[1])
    else:
        for key, reverse in reversed(specs):
            xs.sort(key=itemgetter(key), reverse=reverse)
    return xs


def files_in_dir(file_path):
    """
    Get the files in the specified directory

    Parameters
    ----------
    file_path : str
        Path of input directory.

    Returns
    -------
    flist : list
        Files in input directory.

    """

    flist = []
    for p in Path(file_path).iterdir():
        if p.is_file():
            flist.append(p)

    return flist


def tracksPerStream(tracks):

    minTracksPerStream = min(tracks, key=itemgetter("v", "a", "s"))
    minTracksIdx = tracks.index(minTracksPerStream)

    maxTracksPerStream = max(tracks, key=itemgetter("v", "a", "s"))
    maxTracksIdx = tracks.index(maxTracksPerStream)

    return minTracksPerStream, minTracksIdx, maxTracksPerStream, maxTracksIdx


def compareListOfDicts(list1, list2):

    set_list1 = set(tuple(sorted(d.items())) for d in list1)
    set_list2 = set(tuple(sorted(d.items())) for d in list2)

    set_overlapping = set_list1.intersection(set_list2)
    set_difference = set_list1.symmetric_difference(set_list2)

    list_dicts_difference = []
    for tuple_element in set_difference:
        list_dicts_difference.append(dict((x, y) for x, y in tuple_element))

    return list_dicts_difference


def get_list_items_per_index(user_list, indices):
    return [user_list[i] for i in indices]


def cwd():
    """ Get current working directory """

    return Path(__file__).cwd()


def main():
    # Input arguments
    inputs, output, sort = cli_args()

    # FFprobe the file
    if inputs["type"] == "file":
        all_files = [inputs["path"]]
    elif inputs["type"] == "directory":
        all_files = files_in_dir(inputs["path"])
        # Sort input files alphabetically
        all_files.sort(key=lambda x: str(x))
    else:
        raise Exception(
            "[red]Invalid path type [cyan]{input_type}[/cyan][/red]".format(
                input_type=inputs["type"]
            )
        )

    # Run
    pl = []
    for fl in all_files:
        _, probe_result = probe_file(fl, sort)
        pl.append(probe_result)

    # Check the tracks in every file in the batch for possible inconsistencies
    track_count = []
    files_to_remux = []
    for fx, fs in enumerate(pl):
        tml = {}
        tmc = []
        for s in fs:
            tml[s] = fs[s]["count"]
            tmc = tmc + [f["index"] for f in fs[s]["streams"]]

        track_count.append(tml)

        if list(range(0, len(tmc))) != tmc:
            files_to_remux.append(fx)

    # Get the minimum of video/audio/subtitle tracks (which should be OK for batch)
    (
        minTracksPerStream,
        minTracksIdx,
        maxTracksPerStream,
        maxTracksIdx,
    ) = tracksPerStream(track_count)

    if (minTracksIdx == maxTracksIdx) and not files_to_remux:
        return "No further remuxing steps necessary"

    # Check tracks which are different from "min"
    faulty_probes = []
    faulty_probes_idx = []
    for ix, dc in enumerate(track_count):
        if minTracksPerStream == dc:
            continue

        faulty_probes.append(pl[ix])
        faulty_probes_idx.append(ix)

    # Following files contain more tracks than the base/min file
    good_probe = pl[minTracksIdx]
    to_remove = []
    for xi, ni in zip(faulty_probes_idx, faulty_probes):
        tmp = {all_files[xi].name: {}}
        for st in ni:
            cmp = compareListOfDicts(good_probe[st]["streams"], ni[st]["streams"])
            if cmp:
                tmp[all_files[xi].name][st] = []
                for sst in cmp:
                    tmp[all_files[xi].name][st].append(sst["index"])

        to_remove.append(tmp)

    # Show the inconsistent tracks
    if to_remove:
        print("\r\n> The following inconsistent tracks were found in the batch:\r\n")
        print(to_remove)

    # Get the files/probes to remux
    cfiles = get_list_items_per_index(all_files, files_to_remux)
    cprobes = get_list_items_per_index(pl, files_to_remux)

    # Prepare sorts
    sort_by_key = tuple([("tag:" + el, False) for el in sort])

    # Remux (+ remove unwanted tracks)
    for fl, pr in zip(cfiles, cprobes):
        tridx = next((i for i, d in enumerate(to_remove) if fl.name in d), None)
        if tridx is not None:
            remove_tracks = to_remove[tridx][fl.name]
        else:
            remove_tracks = None

        rmx = remux_file(fl, pr, remove_tracks, output, preferences=sort_by_key)


if __name__ == "__main__":
    """ Main """

    # CWD
    wdir = cwd()

    # Stop execution at keyboard input
    try:
        main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        pass
