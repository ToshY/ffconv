import collections
import functools
import json
import re
from pathlib import Path


def files_in_dir(path: Path, file_types=["*.mkv"]):
    """
    Returns a list of files in the given directory that match the specified file types.

    Parameters:
        path (Path): The path to the directory.
        file_types (List[str], optional): A list of file types to match. Defaults to ["*.mkv"].

    Returns:
        List[Path]: A list of paths to the files in the directory that match the specified file types.
    """

    file_list = [f for f_ in [path.rglob(e) for e in file_types] for f in f_]

    return file_list


def read_json(path: Path) -> dict:
    """
    Reads a JSON file from the given path and returns its contents as a dictionary.

    Parameters:
        path (Path): The path to the JSON file.

    Returns:
        dict: The contents of the JSON file as a dictionary.
    """

    with path.open("r") as file:
        data = json.load(file)

    return data


def remove_empty_dict_values(input_dict: dict) -> dict:
    """
    Removes empty values from a dictionary.

    Parameters:
        input_dict (dict): The dictionary to remove empty values from.

    Returns:
        dict: The input dictionary with empty values removed.
    """

    cleared_data = {k: v for k, v in input_dict.items() if v}

    return cleared_data


def dict_to_list(key_value_dict: dict) -> list:
    """
    Convert a dictionary to a list by concatenating its key-value pairs.

    Parameters:
        key_value_dict (dict): The dictionary to be converted to a list.

    Returns:
        list: A list containing the concatenated key-value pairs from the input dictionary.
    """

    key_value_list = list(functools.reduce(lambda x, y: x + y, key_value_dict.items()))  # type: ignore

    return key_value_list


def split_list_of_dicts_by_key(
    list_of_dicts: list, key: str = "codec_type"
) -> tuple[list[list], list]:
    """
    Splits a list of dictionaries into sublists based on a specified key.

    Parameters:
        list_of_dicts (list): A list of dictionaries to be split.
        key (str, optional): The key to use for splitting. Defaults to "codec_type".

    Returns:
        list: A list of sublists, where each sublist contains dictionaries with the same value for the specified key.
        list: A list of unique values for the specified key.

    """

    result = collections.defaultdict(list)
    keys = []
    for d in list_of_dicts:
        result[d[key]].append(d)
        if d[key] not in keys:
            keys.append(d[key])

    return list(result.values()), keys


def replace_conflicting_characters_in_filename(file_path: Path) -> Path:
    """
    Replaces single and double quotes in filenames for FFmpeg/FFprobe.

    Parameters:
        file_path (Path): The Path object representing the file path.

    Returns:
        Path: The new file path after replacing conflicting characters.
    """

    new_filename = re.sub(r"[\"']", "", file_path.name)
    new_file_path = file_path.with_name(new_filename)
    file_path.rename(new_file_path)

    return new_file_path


def combine_arguments_by_batch(*lists):
    """
    Combine arguments from multiple lists into batches based on the 'batch' key in each item.

    Parameters:
        *lists: Variable number of lists containing dictionaries with a 'batch' key.

    Returns:
        list: A list of dictionaries containing combined items grouped by their 'batch' key.
    """

    combined = collections.defaultdict(dict)

    for lst in lists:
        for item in lst:
            batch = item["batch"]
            combined[batch].update(item)

    result = [value for key, value in combined.items()]

    return result


def preprocess_streams(streams_list):
    """
    Preprocess the streams list by converting it to a dictionary with the stream IDs as keys.
    """

    return {stream["id"]: stream for stream in streams_list}
