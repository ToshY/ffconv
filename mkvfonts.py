# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 20:57:11 2020

@author: ToshY

MKVfonts - Remuxing fonts from folder into MKV

# Example
python mkvfonts.py -i "./input/myfile.mkv" -o "./output" -f "./input/fonts"
"""

import pyfiglet
import argparse
import subprocess as sp
from pathlib import Path
from src.simulate import SimulateLoading
from src.colours import TextColours as tc

class DirCheck(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        for fl in values:
            p = Path(fl).resolve()
            if not p.exists():
                raise FileNotFoundError(f"{tc.RED}The specificed path `{fl}` does not exist.{tc.NC}")
            if p.is_file():
                setattr(args, self.dest, {'path':p,'type':'file'})
            elif p.is_dir():
                setattr(args, self.dest, {'path':p,'type':'directory'})
        
def cli_banner(banner_font='isometric3', banner_colour='OKBLUE', banner_width=200):
    banner = pyfiglet.figlet_format(Path(__file__).stem, font=banner_font, width=banner_width)
    print(f"{tc.CYAN}{banner}{tc.NC}")
    
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
    parser.add_argument('-i','--input',
                        type=str, 
                        required=True,
                        action=DirCheck,
                        nargs='+',
                        help="Path to input file or directory",
    )
    
    parser.add_argument('-o','--output',
                        type=str, 
                        required=True,
                        action=DirCheck,
                        nargs='+',
                        help="Path to output directory",
    )
    
    parser.add_argument('-f','--fonts',
                        type=str, 
                        required=False,
                        action=DirCheck,
                        nargs='+',
                        help="Path to add additional fonts",
    )  
    
    parser.add_argument('-s','--subtitles',
                        type=str, 
                        required=False,
                        action=DirCheck,
                        nargs='+',
                        help="Path to add additional subtitles",
    )
    
    args = parser.parse_args()
    
    return args.input, args.output, args.fonts, args.subtitles

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

def remux_file(input_file, output_dir, fonts, new_file_suffix=' (1)'):
    """
    Remuxing file with specified fonts

    Parameters
    ----------
    input_file : Path
        The specified input file as Path object
    output_dir : Path
        The specified output directory as Path object
    fonts : List
        List of font files as Path objects
    new_file_suffix : str, optional
        Suffix used for filenaming. The default is ' (1)'.

    Returns
    -------
    None.

    """
    
    mkv_fonts = mkv_font_attachments(fonts)

    # Prepare output file
    if output_dir['type'] == 'directory':
        output_file = str(output_dir['path'].joinpath(input_file.stem + new_file_suffix + input_file.suffix))
    else:
        output_file = str(output_dir['path'].parent.joinpath(input_file.stem + new_file_suffix + input_file.suffix))

    input_file_str = str(input_file)
    mkv_cmd = ['mkvmerge','--output', output_file,'(', input_file_str, ')'] + mkv_fonts
    mkv_cmd_verbose = ' '.join(mkv_cmd)
    print('\r\n\r\n> The following MKVmerge command will be executed:\r\n')
    print(mkv_cmd_verbose)
    
    try:
        cprocess = sp.Popen(mkv_cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        # Animate process in terminal
        SL = SimulateLoading('Remuxing')
        return_code = SL.check_probe(cprocess) 

        if return_code != 0:
            raise Exception("MKVmerge returned exit code `{}`.".format(return_code))
            
        return return_code
    except Exception as e:
        raise ("An error occured while trying to remux your file:\n\r{}".format(e.output.decode("utf-8")))
        
    return mkv_cmd

def get_mimetype(file_ext):
    """
    
    Get appropriate mimetype; mimetypes library cannot guess font types

    Parameters
    ----------
    font_file : str
        The specified font file

    Returns
    -------
    str
        The mimetype for the corresponding file extension

    """
    mimes = {'ttf': 'application/x-truetype-font',
             'otf': 'application/vnd.ms-opentype',
             'eot': 'application/vnd.ms-fontobject'}

    return mimes[file_ext.lower()]
    
def mkv_font_attachments(fonts_list):
    """

    Parameters
    ----------
    fonts_list : list
        List of font Path objects

    Returns
    -------
    mkv_fonts : list
        List of MKVmerge attachment commands

    """
    
    mkv_fonts = []
    for font in fonts_list:
        mkv_fonts = mkv_fonts + \
        [
            "--attachment-name",
            font.name,
            "--attachment-mime-type",
            get_mimetype(font.suffix),
            "--attach-file",
            str(font)
        ]
    
    return mkv_fonts

def check_input_in_dir(user_input):
    if user_input['type'] == 'file':
        all_files = [user_input['path']]     
    elif user_input['type'] == 'directory':
        all_files = files_in_dir(user_input['path'])
    else:
        raise Exception('Invalid path type "{input_type}"'.format(input_type=user_input['type']))
        
    return all_files
    
def cwd():
    """ Get current working directory """
    
    return Path(__file__).cwd()

def main():
    # Input arguments
    inputs, output, fonts, subtitles = cli_args()
    
    # Remove Nones    
    all_inputs = check_input_in_dir(inputs)
    all_fonts = check_input_in_dir(fonts)
    all_subtitles = []
    if subtitles is not None:
        all_subtitles = check_input_in_dir(subtitles)

    for fl in all_inputs:
        remux_file(fl, output, all_fonts, new_file_suffix=' (1)')

if __name__ == "__main__":
    """ Main """
    
    # CWD
    wdir = cwd()
    
    # Stop execution at keyboard input
    try:
        main()
    except KeyboardInterrupt:
        print('\r\n\r\n> Execution cancelled by user')
        pass