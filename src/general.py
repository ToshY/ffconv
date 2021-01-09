# -*- coding: utf-8 -*-
"""
Created on Thu Dec  12 20:52:08 2020

@author: ToshY
"""

import collections
import functools
import json


def read_file(
    input_file: str, split_lines: bool = True, custom_encoding: str = "latin-1"
) -> list:
    """
    Read in file

    Parameters
    ----------
    file_name : str
        Input file name.

    Returns
    -------
    list
        Output.

    """

    input_file_read = open(str(input_file), mode="r", encoding=custom_encoding).read()

    if split_lines:
        return {"content": input_file_read.splitlines(), "encoding": custom_encoding}

    return {"content": input_file_read, "encoding": custom_encoding}


def read_json(input_file: str) -> dict:
    """
    Read in JSON file.

    Parameters
    ----------
    input_file : str
        The specified input JSON file.

    Returns
    -------
    data : dictonary
        The data in JSON format.

    """

    with open(input_file) as json_file:
        data = json.load(json_file)

    return data


def find_in_dict(input_list: list, key: str, value: str):
    """
    Find in current list with dictonaries.

    Parameters
    ----------
    lst : list
        Input list
    key : str
        Key to use.
    value : str
        Value to find.

    Returns
    -------
    TYPE : int | bool
        Returns the index of found elemnt or False.

    """
    for i, dic in enumerate(input_list):
        if dic[key] == value:
            return i

    return False


def remove_empty_dict_values(input_dict: dict) -> dict:
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


def dict_to_list(key_value_dict: dict) -> list:
    """
    Convert dictonary key/values to 1D key:value list

    Parameters
    ----------
    input_dict : dict
        The specified input dictonary

    Returns
    -------
    key_value_list : list
        List of key:value arguments

    """

    key_value_list = list(functools.reduce(lambda x, y: x + y, key_value_dict.items()))

    return key_value_list


def dict_to_tuple(key_value_dict: dict) -> list:
    """
    Convert dictonary key/values to 2D list of key,value tuples

    Parameters
    ----------
    input_dict : dict
        The specified input dictonary

    Returns
    -------
    key_value_list : list
        List of key:value arguments

    """

    key_value_list = [(k, v) for k, v in key_value_dict.items()]

    return key_value_list


def list_to_dict(key_value_list: list) -> dict:
    """
    Convert 1D list to key:value pairs

    Parameters
    ----------
    key_value_list : list
        The specified input list

    Returns
    -------
    key_value_dict : dict
        Dict of key-value pair

    """

    key_value_dict = dict(zip(key_value_list[::2], key_value_list[1::2]))

    return key_value_dict


def split_list_of_dicts_by_key(list_of_dicts: list, key: str = "codec_type") -> list:
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

    return list(result.values()), keys
