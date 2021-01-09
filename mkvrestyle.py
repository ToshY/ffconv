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
import argparse
import json
import itertools as it
import subprocess as sp
from collections import Counter
from pathlib import Path
from src.banner import cli_banner
from src.table import table_print_stream_options
from src.args import FileDirectoryCheck, files_in_dir
from src.general import read_file, read_json, remove_empty_dict_values
from src.fonts import FontFinder
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
        action=FileDirectoryCheck,
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
        ssdata = ["-1"]

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
                    raise Exception(
                        f"The path `{str(cpath)}` contains"
                        f" `{len_all_files_in_batch}`files but only"
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


def get_lines_per_type(my_lines, split_at=["Format: "]):
    return [
        (i, [x for x in re.split("|".join(split_at) + "|,[\s]?", s) if x])
        for i, s in enumerate(my_lines)
        if any(s.startswith(xs) for xs in split_at)
    ]


def get_lines_per_format(my_lines):
    rgx_style = r"^([Format]+):\s(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+)$"
    rgx_dialogue = r"^([Format]+):\s(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+),[\s]?(\w+)$"
    format_line_style = [
        (i, list(re.findall(rgx_style, x)[0]))
        for i, x in enumerate(my_lines)
        if any(x.startswith(xs) for xs in ["Format: Name"])
    ]
    format_line_dialogue = [
        (i, list(re.findall(rgx_dialogue, x)[0]))
        for i, x in enumerate(my_lines)
        if any(x.startswith(xs) for xs in ["Format: Layer"])
    ]
    format_lines = format_line_style + format_line_dialogue
    if len(format_lines) > 2:
        raise Exception(
            "Invalid ASS syntax. The original ASS contains more than 2 format lines in total."
        )
    return {"style": format_lines[0], "dialogue": format_lines[1]}


def get_lines_per_dialogue(my_lines, keys):
    rgx = r"^^([Dialogue]+|[Comment]+):\s(\d{1,}),(\d{1}:\d{2}:\d{2}.\d{2}),(\d{1}:\d{2}:\d{2}.\d{2}),(.*?),(.*?),([0-9.]{1,4}),([0-9.]{1,4}),([0-9.]{1,4}),([$^,]?|[^,]+?)?,(.*?)$"
    dialogue_lines = [
        (i, dict(zip(keys, list(re.findall(rgx, x)[0]))))
        for i, x in enumerate(my_lines)
        if any(x.startswith(xs) for xs in ["Dialogue", "Comment"])
    ]
    return dialogue_lines


def get_lines_per_style(my_lines, keys, split_at=["Style: "]):
    rgx = r"^([Style]+):\s(.*?),(.*?),([0-9.]{1,}),(&H[a-fA-F0-9]{8}),(&H[a-fA-F0-9]{8}),(&H[a-fA-F0-9]{8}),(&H[a-fA-F0-9]{8}),(0|-1),(0|-1),(0|-1),(0|-1),([0-9.]{1,}),([0-9.]{1,}),([0-9.]{1,}),([0-9.]{1,}),(1|3),([0-9.]{1,}),([0-9.]{1,}),([1-9]),([0-9.]{1,4}),([0-9.]{1,4}),([0-9.]{1,4}),(\d{1,3})$"
    style_lines = [
        (i, dict(zip(keys, list(re.findall(rgx, x)[0]))))
        for i, x in enumerate(my_lines)
        if any(x.startswith(xs) for xs in ["Style"])
    ]
    return style_lines


def prepare_track_info(file, index, codec, lang):
    return file.stem + "_track" + str(index) + "_" + lang + subs_mimetype(codec)


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
            "language": sub["properties"]["language"]
            if "language" in sub["properties"]
            else "",
            "title": sub["properties"]["track_name"]
            if "track_name" in sub["properties"]
            else "",
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
    if stream_select == "-1":
        selected_subs = ass_subs[0]["index"]
        # Request user input for stream type
        if len(ass_subs) > 1:
            print("\r\n> Multiple [cyan]subtitle[/cyan] streams detected")

            # Print the options
            table_print_stream_options(ass_subs)
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
                sub["index"] for sub in ass_subs if sub["language"] == stream_select
            )

    selected_subs = next(
        sub for sub in ass_subs if int(sub["index"]) == int(selected_subs)
    )
    ass_track_path = Path(os.path.join(save_loc, selected_subs["save_file"]))

    # MKVextract subtitle track
    mkv_subs = [
        "mkvextract",
        "tracks",
        input_file_str,
        f'{selected_subs["index"]}:{ass_track_path}',
    ]
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
        font_info = [
            {**{"file_path": Path(el)}, **FF.font_info_by_file(el)} for el in font_files
        ]

        return (
            [selected_subs["save_file"], ass_track_path, available_fonts],
            font_info,
        )

    return [selected_subs["save_file"], ass_track_path, available_fonts], []


def get_available_fonts(fonts_list: dict, font_names_list: list) -> list:
    fonts_available = {}
    for font in font_names_list:
        fonts_available[font] = next(
            (item for item in fonts_list if item["font_name"] == font), False
        )

    return fonts_available


def check_available_fonts(fs_fonts: dict, em_fonts: dict, key: str):
    if (fs_fonts[key] is False) & (em_fonts[key] is False):
        raise Exception(
            "The font `{key}` could not be found on the filesystem and could also not be found as an extracted attachment from the source file."
        )
    elif (fs_fonts[key] is False) and (em_fonts[key] is not False):
        main_font = em_fonts[key]
    elif (fs_fonts[key] is not False) and (em_fonts[key] is False):
        main_font = fs_fonts[key]
    else:
        main_font = em_fonts[key]

    return main_font


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
        font_files.append(fl)
        font_files_extract.append("{}:{}".format(el["id"], fl))

    return font_files, font_files_extract


def resample_mean(dimensions_list_one, dimensions_list_two):
    mean_factor = (
        (int(dimensions_list_one[0]) / int(dimensions_list_two[0]))
        + (int(dimensions_list_one[1]) / int(dimensions_list_two[1]))
    ) / 2

    return mean_factor


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
                fl, fl_attachments_folder, b["subtitle_stream_select"][y]
            )

            # Read subs
            read_file_content = read_file(ass[1], True)
            lines = read_file_content["content"]

            # Get Resolution/Format/Styles/Dialogues indices
            ass_resolution = {
                "PlayResX": get_lines_per_type(lines, ["PlayResX: "])[0],
                "PlayResY": get_lines_per_type(lines, ["PlayResY: "])[0],
            }
            format_lines = get_lines_per_format(lines)
            style_lines = get_lines_per_style(lines, format_lines["style"][1])
            dialogue_lines = get_lines_per_dialogue(lines, format_lines["dialogue"][1])

            # Style names
            style_names = list(set([el[-1]["Name"] for el in style_lines]))

            # Style names from dialogue
            style_names_dialogue_all = [el[-1]["Style"] for el in dialogue_lines]
            style_names_dialogue = list(set(style_names_dialogue_all))

            # Find the dialogue styles which exist and which not in Styles
            style_lines_kept = [
                el for el in style_lines if el[-1]["Name"] in style_names_dialogue
            ]
            style_lines_remove = [
                el for el in style_lines if el[-1]["Name"] not in style_names_dialogue
            ]

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
            ffdims["PlayResX"] = ffdims.pop("width")
            ffdims["PlayResY"] = ffdims.pop("height")

            # Calculate resample mean between video dimensions and preset
            ass_resample_mean = resample_mean(
                [ffdims["PlayResX"], ffdims["PlayResY"]],
                [ass_resolution["PlayResX"][-1][0], ass_resolution["PlayResY"][-1][0]],
            )

            # Resample ASS to video dimensions and user preset
            for ids, (line, style) in enumerate(style_lines_kept):
                for key in style:
                    if key in [
                        "Fontsize",
                        "ScaleX",
                        "ScaleY",
                        "Spacing",
                        "Outline",
                        "Shadow",
                        "MarginL",
                        "MarginR",
                        "MarginV",
                    ]:
                        if int(style[key]) != 0:
                            if key not in ["ScaleX", "ScaleY"]:
                                style[key] = round(
                                    float(style[key]) * ass_resample_mean, 2
                                )
                            preset_key_dict = sub_settings[key]
                            if preset_key_dict:
                                resampled_value = round(
                                    float(style[key])
                                    * float(preset_key_dict["factor"]),
                                    preset_key_dict["round"],
                                )
                                if preset_key_dict["round"] == 0:
                                    resampled_value = int(resampled_value)
                                style[key] = str(resampled_value)

                # Change original line to resampled line
                format_type = dict(it.islice(style.items(), 1))["Format"]
                format_values = list(dict(it.islice(style.items(), 1, None)).values())
                lines[line] = "{}: {}".format(format_type, ",".join(format_values))

            # Resample dialogue margins
            for idd, (line, dialogue) in enumerate(dialogue_lines):
                for key in dialogue:
                    if key in ["MarginL", "MarginR", "MarginV"]:
                        if int(dialogue[key]) != 0:
                            dialogue[key] = round(
                                float(dialogue[key]) * ass_resample_mean, 2
                            )
                            preset_key_dict = sub_settings[key]
                            if preset_key_dict:
                                resampled_value = round(
                                    float(dialogue[key])
                                    * float(preset_key_dict["factor"]),
                                    preset_key_dict["round"],
                                )
                                if preset_key_dict["round"] == 0:
                                    resampled_value = int(resampled_value)
                                dialogue[key] = str(resampled_value)

                # Change original line to resampled line
                format_type = dict(it.islice(dialogue.items(), 1))["Format"]
                format_values = list(
                    dict(it.islice(dialogue.items(), 1, None)).values()
                )
                lines[line] = "{}: {}".format(format_type, ",".join(format_values))

            # Check font preset options
            font_settings = sub_settings["FontName"]
            font_name = font_settings["name"]
            if not isinstance(font_name, str):
                raise Exception(
                    f"Invalid font name `{font_name}` provided. Please provide and empty string or valid font name."
                )

            font_option = font_settings["option"]
            # Set font option to 0 if no font provided
            if (font_name == "") | (font_option < 0) | (font_option > 2):
                font_option == 0

            # Style font replacement (from ASS styles)
            font_names_kept = [*{*[el[-1]["Fontname"] for el in style_lines_kept]}]

            # Font replacement; 2 = all; 1 = main; 0 = none
            if font_option == 2:
                # Preset font availability
                fonts_filesystem = get_available_fonts(ass[2], [font_name])
                fonts_embed = get_available_fonts(fonts, [font_name])

                print(fonts_filesystem, fonts_embed, font_name)
                main_fonts_preset = check_available_fonts(
                    fonts_filesystem, fonts_embed, font_name
                )

                # Replacement of every existing style
                style_lines = get_lines_per_style(lines, format_lines["style"][1])
                for (line, style) in style_lines:
                    for key in style:
                        if key == "Fontname":
                            style[key] = main_fonts_preset["font_name"]

                    # Change original line to resampled line
                    format_type = dict(it.islice(style.items(), 1))["Format"]
                    format_values = list(
                        dict(it.islice(style.items(), 1, None)).values()
                    )
                    lines[line] = "{}: {}".format(format_type, ",".join(format_values))
            elif font_option == 1:
                # Preset font availability
                fonts_filesystem = get_available_fonts(ass[2], [font_name])
                fonts_embed = get_available_fonts(fonts, [font_name])

                main_fonts_preset = check_available_fonts(
                    fonts_filesystem, fonts_embed, font_name
                )

                # ASS font availability
                fonts_filesystem = get_available_fonts(ass[2], font_names_kept)
                fonts_embed = get_available_fonts(fonts, font_names_kept)

                main_fonts_ass = []
                for (fname, filesystem_font), (_, embed_font) in zip(
                    fonts_filesystem.items(), fonts_embed.items()
                ):
                    main_fonts_ass.append(
                        check_available_fonts(
                            {fname: filesystem_font}, {fname: embed_font}, fname
                        )
                    )

                # Get most occuring style name
                style_occurence = Counter(style_names_dialogue_all)
                max_occuring_style_name = max(style_occurence, key=style_occurence.get)
                # Get corresponding font for style to replace
                max_occuring_style = next(
                    (
                        item
                        for item in style_lines_kept
                        if item[1]["Name"] == max_occuring_style_name
                    ),
                    False,
                )
                max_occuring_font = max_occuring_style[1]["Fontname"]

                # Replacement of most occuring font (e.g. in main/top/italic) by preset font
                style_lines = get_lines_per_style(lines, format_lines["style"][1])
                for (line, style) in style_lines:
                    for key in style:
                        if (key == "Fontname") & (style[key] == max_occuring_font):
                            style[key] = main_fonts_preset["font_name"]

                    # Change original line to resampled line
                    format_type = dict(it.islice(style.items(), 1))["Format"]
                    format_values = list(
                        dict(it.islice(style.items(), 1, None)).values()
                    )
                    lines[line] = "{}: {}".format(format_type, ",".join(format_values))

            else:
                # ASS font availability
                fonts_filesystem = get_available_fonts(ass[2], font_names_kept)
                fonts_embed = get_available_fonts(fonts, font_names_kept)

                main_fonts_ass = []
                for (fname, filesystem_font), (_, embed_font) in zip(
                    fonts_filesystem.items(), fonts_embed.items()
                ):
                    main_fonts_ass.append(
                        check_available_fonts(
                            {fname: filesystem_font}, {fname: embed_font}, fname
                        )
                    )

            # Replace PlayRes by video dimension
            for (direction, (line, _)) in ass_resolution.items():
                lines[line] = f"{direction}: {ffdims[direction]}"

            # Remove unnecessary styles
            lines = [
                el
                for idx, el in enumerate(lines)
                if idx not in [idy for idy, style in style_lines_remove]
            ]

            # Overwrite ASS
            with open(ass[1], "w", encoding=read_file_content["encoding"]) as f:
                f.write("\n".join(item for item in lines))

            # Remux file back; TODO


if __name__ == "__main__":
    """ Main """
    cli_banner(__file__)

    # Stop execution at keyboard input
    try:
        resl = main()
    except KeyboardInterrupt:
        print("\r\n\r\n> [red]Execution cancelled by user[/red]")
        exit()
