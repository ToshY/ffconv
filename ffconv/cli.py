import json
from datetime import datetime
from pathlib import Path

import click
from rich.prompt import IntPrompt

from ffconv.args import (
    InputPathChecker,
    OutputPathChecker,
    PresetPathChecker,
    OptionalValueChecker,
    PresetOptionalChecker,
)
from ffconv.exception import StreamOrderError, StreamTypeMissingError
from ffconv.helper import (
    split_list_of_dicts_by_key,
    combine_arguments_by_batch,
    remove_empty_dict_values,
    dict_to_list,
)
from ffconv.process import ProcessCommand
from ffconv.table import table_print_stream_options
from loguru import logger  # noqa


def validate_stream_order(mkvmerge_identify_result):
    """
    Check the order of streams in the given ffprobe result.

    Parameters:
        mkvmerge_identify_result (dict): A dictionary containing the ffprobe result.
            The keys are the stream types (e.g., 'video', 'audio', 'subtitle') and the values
            are dictionaries with the following keys:
            - 'count' (int): The number of streams of that type.
            - 'streams' (list): A list of dictionaries, each representing a stream.
                Each stream dictionary has the following keys:
                - 'id' (int): The ID of the stream.
                - 'properties' (dict): A dictionary containing additional properties of the stream.

    Raises:
        StreamOrderError: If the stream orders are not standardized.

    Returns:
        None
    """

    total_streams = list(
        range(0, sum([st["count"] for ix, st in mkvmerge_identify_result.items()]))
    )

    # Check count and properly formatted file
    for stream_type, stream_info in mkvmerge_identify_result.items():
        stream_count = stream_info["count"]
        if total_streams[:stream_count] != [
            current_stream["id"] for current_stream in stream_info["streams"]
        ]:
            raise StreamOrderError()

        del total_streams[:stream_count]


def validate_stream_count(mkvmerge_identify_result):
    """
    Check the stream count in the given ffprobe result.

    Parameters:
        mkvmerge_identify_result (dict): A dictionary containing the ffprobe result.
            The keys are the stream types (e.g., 'video', 'audio', 'subtitle') and the values
            are dictionaries with the following keys:
            - 'count' (int): The number of streams of that type.

    Raises:
        StreamTypeMissingError: If any stream count is less than 1.

    Returns:
        None
    """

    for stream_type, stream_info in mkvmerge_identify_result.items():
        if stream_info["count"] < 1:
            raise StreamTypeMissingError(stream_type)


def stream_user_input(mkvmerge_identify_result):
    """
    Get stream ID from user input.

    Parameters:
        mkvmerge_identify_result (dict): A dictionary containing the ffprobe result.
            The keys are the stream types (e.g., 'video', 'audio', 'subtitle') and the values
            are dictionaries with the following keys:
            - 'count' (int): The number of streams of that type.
            - 'streams' (list): A list of dictionaries, each representing a stream.
                Each stream dictionary has the following keys:
                - 'id' (int): The ID of the stream.
                - 'properties' (dict): A dictionary containing additional properties of the stream.

    Raises:
        StreamTypeMissingError: If any stream count is less than 1.

    Returns:
        None
    """

    stream_map = {}
    stream_sum_count = 0
    for stream_type, stream_info in mkvmerge_identify_result.items():
        if stream_info["count"] == 0:
            raise StreamTypeMissingError(stream_type)
        if stream_info["count"] == 1:
            stream_map[stream_type] = stream_info["streams"][0]["id"]
        else:
            logger.info(f"Multiple `{stream_type}` streams detected")

            # Default
            selected_stream = stream_info["streams"][0]["id"]

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
                    "default": (
                        cs["properties"]["default_track"]
                        if "default_track" in cs["properties"]
                        else "n/a"
                    ),
                }
                for cs in stream_info["streams"]
            ]

            table_print_stream_options(stream_properties)
            allowed = [str(cs["id"]) for cs in stream_properties]

            # Request user input
            selected_stream = IntPrompt.ask(
                f"# Please specify the {stream_type} id to use: ",
                choices=allowed,
                default=selected_stream,
                show_choices=True,
                show_default=True,
            )
            logger.info(f"Selected stream index: {selected_stream}")
            stream_map[stream_type] = selected_stream

        # Remap subtitle due to filter complex
        if stream_type != "subtitles":
            stream_sum_count = stream_sum_count + stream_info["count"]
        else:
            stream_map[stream_type] = int(stream_map[stream_type]) - stream_sum_count

    return stream_map


def mkvmerge_identify_streams(
    input_file, total_items, item_index, batch_index, batch_name
):
    """
    Identify and parse the streams in an MKV file.

    Parameters:
        input_file (Path): The path to the input MKV file.
        total_items (int): The total number of items in the batch.
        item_index (int): The index of the current item.
        batch_index (int): The index of the batch.
        batch_name (str): The name of the batch.

    Returns:
        tuple: A tuple containing the parsed streams and the mapping.
            - streams (dict): A dictionary containing the parsed streams.
                The keys are the stream types (e.g., 'video', 'audio', 'subtitle') and the values
                are dictionaries with the following keys:
                - 'count' (int): The number of streams of that type.
                - 'streams' (list): A list of dictionaries, each representing a stream.
                    Each stream dictionary has the following keys:
                    - 'id' (int): The ID of the stream.
                    - 'properties' (dict): A dictionary containing additional properties of the stream.
            - mapping (dict or None): The mapping for stream conversion, if applicable.
    """

    if item_index == 0:
        logger.info(
            f"MKVmerge identify batch `{batch_index}` for `{batch_name}` started."
        )

    mkvmerge_identify_command = [
        "mkvmerge",
        "--identify",
        "--identification-format",
        "json",
        str(input_file),
    ]

    process = ProcessCommand(logger)
    result = process.run("MKVmerge identify", mkvmerge_identify_command)

    mkvmerge_identify_output = json.loads(result.stdout)

    # Split by codec_type
    split_streams, split_keys = split_list_of_dicts_by_key(
        mkvmerge_identify_output["tracks"], "type"
    )

    # Rebuild streams & count per codec type
    streams = {k: {"streams": {}, "count": 0} for k in split_keys}
    for x, s in enumerate(split_keys):
        streams[s]["streams"] = split_streams[x]
        streams[s]["count"] = len(streams[s]["streams"])

    validate_stream_count(streams)
    validate_stream_order(streams)

    # Check if first file from batch for mapping in conversion later
    mapping = None
    if item_index == 0:
        mapping = stream_user_input(streams)

    if item_index == total_items - 1:
        logger.info(
            f"MKVmerge identify batch `{batch_index}` for `{batch_name}` completed."
        )

    return streams, mapping


def ffmpeg_convert_file(
    input_file: Path,
    output_path: Path,
    output_extension: str,
    stream_mapping: dict,
    video_preset: dict,
    audio_preset: dict,
    filter_preset: dict | None,
    total_items: int,
    item_index: int,
    batch_index: int,
    batch_name: str,
):
    """
    Convert an input file to an output file using FFmpeg.

    Parameters:
        input_file (Path): The path to the input file.
        output_path (Path): The path to the output directory or file.
        output_extension (str): The extension of the output file.
        stream_mapping (dict): The mapping for stream conversion.
        video_preset (dict): The video preset.
        audio_preset (dict): The audio preset.
        filter_preset (dict): The filter preset.
        total_items (int): The total number of items in the batch.
        item_index (int): The index of the current item.
        batch_index (int): The index of the batch.
        batch_name (str): The name of the batch.
    """

    # Converting presets to lists and clearing empty values
    video_preset_list = dict_to_list(remove_empty_dict_values(video_preset))
    audio_preset_list = dict_to_list(remove_empty_dict_values(audio_preset))

    if item_index == 0:
        logger.info(f"FFmpeg batch `{batch_index}` for `{batch_name}` started.")

    output_extension_with_leading_dot = "." + output_extension.lstrip(".")
    if output_path.is_dir():
        output_file = output_path.joinpath(
            input_file.stem + output_extension_with_leading_dot
        )
    else:
        output_file = Path(
            f"{output_path.with_suffix('')}{output_extension_with_leading_dot}"
        )

    # Prepare mapping data
    video_map_index = "0:" + str(stream_mapping["video"])
    audio_map_index = "0:" + str(stream_mapping["audio"])

    # Filter complex subtitle map requires this escaped monstrosity for Windows
    lit_file = str(input_file).replace("\\", "\\\\").replace(":", "\:")
    filter_complex_map = (
        "subtitles='" + lit_file + "':si=" + str(stream_mapping["subtitles"]),
    )

    # Additional filter complex options; added due to possible issues with subtitles using BT.709 color space
    if filter_preset is not None:
        filter_complex_data_before = filter_preset.get("before", "")
        if len(filter_complex_data_before.strip()):
            filter_complex_map = (  # type: ignore[assignment]
                filter_complex_data_before.strip().rstrip(","),
                *filter_complex_map,
            )

        filter_complex_data_after = filter_preset.get("after", "")
        if len(filter_complex_data_after.strip()):
            filter_complex_map = (  # type: ignore[assignment]
                *filter_complex_map,
                filter_complex_data_after.strip().lstrip(","),
            )

    filter_complex_map_concat = ",".join(filter_complex_map)
    filter_complex_map_complete = f"[{video_map_index}]{filter_complex_map_concat}"

    current_datetime = datetime.now()
    metadata_encoded_date = (
        f'comment=Encoded on {current_datetime.strftime("%Y-%m-%d %H:%M:%S")}'
    )

    ffmpeg_convert_command = (
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
            metadata_encoded_date,
            "-map",
            audio_map_index,
            "-filter_complex",
            filter_complex_map_complete,
        ]
        + video_preset_list
        + audio_preset_list
        + ["-movflags", "faststart", str(output_file)]
    )

    process = ProcessCommand(logger)
    process.run("FFmpeg convert", ffmpeg_convert_command)

    if item_index != total_items - 1:
        return

    logger.info(f"FFmpeg batch `{batch_index}` for `{batch_name}` completed.")


@logger.catch
@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog="Repository: https://github.com/ToshY/ffconv",
)
@click.option(
    "--input-path",
    "-i",
    type=click.Path(exists=True, dir_okay=True, file_okay=True, resolve_path=True),
    required=False,
    multiple=True,
    callback=InputPathChecker(),
    show_default=True,
    default=["./input"],
    help="Path to input file or directory",
)
@click.option(
    "--output-path",
    "-o",
    type=click.Path(dir_okay=True, file_okay=True, resolve_path=True),
    required=False,
    multiple=True,
    callback=OutputPathChecker(),
    show_default=True,
    default=["./output"],
    help="Path to output file or directory",
)
@click.option(
    "--video-preset",
    "-vp",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, resolve_path=True),
    required=False,
    multiple=True,
    callback=PresetPathChecker(),
    show_default=True,
    default=["./preset/video.json"],
    help="Path to JSON file with video preset options",
)
@click.option(
    "--audio-preset",
    "-ap",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, resolve_path=True),
    required=False,
    multiple=True,
    callback=PresetPathChecker(),
    show_default=True,
    default=["./preset/audio.json"],
    help="Path to JSON file with audio preset options",
)
@click.option(
    "--filter-preset",
    "-fp",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, resolve_path=True),
    required=False,
    multiple=True,
    callback=PresetOptionalChecker(),
    show_default=True,
    default=[None],
    help="Path to JSON file with filter complex preset options",
)
@click.option(
    "--extension",
    "-ext",
    type=click.Choice(["mp4", "webm", "avi"]),
    required=False,
    multiple=True,
    callback=OptionalValueChecker(),
    show_default=True,
    default=["mp4"],
    help="Output file extension",
)
@click.option(
    "--auto-audio-preset",
    is_flag=True,
    show_default=True,
    default=False,
    help="Automatically decides audio preset to use based on audio stream codec",
)
def cli(
    input_path,
    output_path,
    video_preset,
    audio_preset,
    filter_preset,
    extension,
    auto_audio_preset,
):
    # auto_decide_presets = auto
    combined_result = combine_arguments_by_batch(
        input_path, output_path, video_preset, audio_preset, filter_preset, extension
    )

    # Identify streams
    for item in combined_result:
        current_batch = item.get("batch")
        current_input_original_batch_name = item.get("input").get("given")
        current_input_files = item.get("input").get("resolved")
        total_current_input_files = len(current_input_files)

        stream_mapping = None
        for current_file_path_index, current_file_path in enumerate(
            current_input_files
        ):
            mkvmerge_identify_result, mapping = mkvmerge_identify_streams(
                current_file_path,
                total_current_input_files,
                current_file_path_index,
                current_batch,
                current_input_original_batch_name,
            )

            if mapping is None:
                continue

            stream_mapping = mapping

        item["stream_mapping"] = stream_mapping

    # Convert
    for item in combined_result:
        current_batch = item.get("batch")
        current_video_preset = item.get("video_preset")
        current_audio_preset = item.get("audio_preset")
        current_filter_preset = item.get("filter_preset")
        current_output_extension = item.get("extension")
        current_stream_mapping = item.get("stream_mapping")
        current_output = item.get("output").get("resolved")
        current_input_original_batch_name = item.get("input").get("given")
        current_input_files = item.get("input").get("resolved")
        total_current_input_files = len(current_input_files)

        for current_file_path_index, current_file_path in enumerate(
            current_input_files
        ):
            ffmpeg_convert_file(
                current_file_path,
                current_output,
                current_output_extension,
                current_stream_mapping,
                current_video_preset,
                current_audio_preset,
                current_filter_preset,
                total_current_input_files,
                current_file_path_index,
                current_batch,
                current_input_original_batch_name,
            )
