# -*- coding: utf-8 -*-

import argparse
import mimetypes
from pathlib import Path
from rich.traceback import install

install()


def current_working_dir():
    """
    Get current working directory.

    Returns
    -------
    Path.
    """

    return Path(__file__).cwd()


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
        List of Path objects of specified directory.

    """

    flist = [f for f_ in [Path(file_path).rglob(e) for e in file_types] for f in f_]

    return flist


class FileDirectoryCheck(argparse.Action):
    """
    Checks if the specified input file or directory exists.
    If constant is set to false, directories that do not exists will be created.
    """

    def __call__(self, parser, args, values, option_string=None):
        """
        File/Directory argument checks

        Parameters
        ----------
        parser
            Argument parser.
        args
            Arguments.
        values
            Argument values.
        option_string
            Descriptional string. The default is None.

        Raises
        ------
        FileNotFoundError
            The specified File or Directory could not resolved.

        Returns
        -------
        None.

        """
        all_values = []
        for fl in values:
            p = Path(fl).resolve()
            if not self.const:
                if p.suffix:
                    if not p.parent.is_dir():
                        raise FileNotFoundError(
                            f"The parent directory `{str(p.parent)}` "
                            "for output argument `{str(p)}` does not exist."
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
                        f"The specificed path `{fl}` does not exist."
                    )
                if p.is_file():
                    all_values.append({p: "file"})
                else:
                    all_values.append({p: "directory"})

        setattr(args, self.dest, all_values)


class ExtensionCheck(argparse.Action):
    """
    Checks if the specified extension is valid through mimetype guessing.
    """

    def __call__(self, parser, args, values, option_string=None):
        """
        File extension argument checks

        Parameters
        ----------
        parser
            Argument parser.
        args
            Arguments.
        values
            Argument values.
        option_string
            Descriptional string. The default is None.

        Raises
        ------
        ValueError
            The specified output extension is not a valid extension for video files.

        Returns
        -------
        None.

        """
        mimetypes.init()
        stripped_ext = values.lstrip(".")
        ext_check = "placeholder." + stripped_ext
        mime_output = mimetypes.guess_type(ext_check)[0]
        if "video" not in mime_output:
            raise ValueError(
                f"The specificed output extension `{stripped_ext}` "
                "is not a valid video extension."
            )
        setattr(args, self.dest, {"extension": stripped_ext})
