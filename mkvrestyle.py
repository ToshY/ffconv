# -*- coding: utf-8 -*-
"""
Created on Sat Nov 14 17:11:27 2020

@author: ToshY

MKVrestyle - Restyle the main font styling of the embedded ASS file

# Example
python mkvrestyle.py -i "./input/" -o "./output/" -sp "./preset/subtitle_preset.json"
"""

import os
import sys
import re
import argparse
import mimetypes
import json
import pyfiglet
import subprocess as sp
import functools as fc
from contextlib import redirect_stderr
from operator import itemgetter 
from pathlib import Path
from contextlib import redirect_stderr
from fontTools import ttLib
from pymediainfo import MediaInfo
from src.simulate import SimulateLoading
from src.colours import TextColours as tc

class DirCheck(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        all_values = []
        for fl in values:
            p = Path(fl).resolve()
            if not p.exists():
                raise FileNotFoundError(f"{tc.RED}The specificed path `{fl}` does not exist.{tc.NC}")
            if p.is_file():
                all_values.append({p:'file'})
                continue
            all_values.append({p:'directory'})
            
        setattr(args, self.dest, all_values)
        
class ExtCheck(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        mimetypes.init()
        stripped_ext = values.lstrip('.')
        ext_check = 'placeholder.' + stripped_ext
        mime_output = mimetypes.guess_type(ext_check)[0]
        if 'video' not in mime_output:
            raise ValueError(f"{tc.RED}The specificed output extension `{stripped_ext}` is not a valid video extension.{tc.NC}")
        setattr(args, self.dest, {'extension': stripped_ext})
        
def cli_banner(banner_font='isometric3', banner_width=200):
    banner = pyfiglet.figlet_format(Path(__file__).stem, font=banner_font, width=banner_width)
    print(f"{tc.CYAN}{banner}{tc.NC}")

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
    parser.add_argument('-sp','--subtitle_preset',
                        type=str, 
                        required=True,
                        action=DirCheck,
                        nargs='+',
                        help="Path to JSON file with ASS video preset options",
    )
    parser.add_argument('-w','--overwrite',
                        type=bool,
                        default=1
    )
    args = parser.parse_args()
    
    # Check args count
    #user_args = check_args(args.input, args.output, args.video_preset, args.audio_preset)
    
    return args.input, args.output, args.subtitle_preset, args.overwrite

def read_subs(file_name):
    """
    Read in file

    Parameters
    ----------
    file_name : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    """
    
    return open(str(*file_name), mode='r').read().splitlines()

def get_lines_per_type(my_lines, split_at=['Format: ']):
    return [(i,[x for x in re.split('|'.join(split_at)+'|,', s) if x])  for i,s in enumerate(my_lines) if any(s.startswith(xs) for xs in split_at)]

def additional_info():
    return {'WrapStyle': '0','ScaledBorderAndShadow': 'yes','YCbCr Matrix': 'TV.709'}    

def extract_subsnfonts(input_file, save_loc):
    
    # file str
    input_file_str = str(input_file)

    mkv_cmd = ['mkvmerge','--identify','--identification-format','json', input_file_str]
    cprocess = sp.run(mkv_cmd,capture_output=True)

    # Json output
    mkvout = json.loads(cprocess.stdout)
    
    # Get attachments
    attachments = mkvout['attachments']
    tracks = mkvout['tracks']
    
    ass_subs = next(item for item in tracks if item["codec"] == "SubStationAlpha")
    ass_subs_idx = ass_subs['id']
    ass_track_name = input_file.stem + '_track' + str(ass_subs_idx) + subs_mimetype(ass_subs['properties']['codec_id'])
    
    # MKVextract subtitle track
    mkv_subs = ['mkvextract','tracks', input_file] + ['0:' + os.path.join(save_loc, ass_track_name)]
    
    # To export fonts
    exp_font_list, font_files_loc = export_fonts_list(attachments, save_loc)
    
    # MKVextract attachments
    mkv_attachments = ['mkvextract','attachments', input_file] + exp_font_list
    
    # Get font names
    fns = [get_font_name(el) for el in font_files_loc]
            
    return fns

def subs_mimetype(codec_id):
    if codec_id.lower() == 's_text/ass':
        return '.ass'
    elif codec_id.lower() == 'text/plain':
        return '.srt'
    else:
        raise Exception(f"Invalid codec `{codec_id}`")
        
def export_fonts_list(attachments, save_loc):
    ex_args = []
    font_files = []
    for el in attachments:
        fl = os.path.join(save_loc, el['file_name'])
        font_files.append(fl)
        ex_args.append('{}:{}'.format(el['id'], fl))
    
    return ex_args, font_files
    
def get_font_name(font_path):
    font = ttLib.TTFont(font_path, ignoreDecompileErrors=True)
    with redirect_stderr(None):
        names = font['name'].names

    details = {}
    for x in names:
        if x.langID == 0 or x.langID == 1033:
            try:
                details[x.nameID] = x.toUnicode()
            except UnicodeDecodeError:
                details[x.nameID] = x.string.decode(errors='ignore')

    return {'name':details[4],'family':details[1],'style':details[2]}

def cwd():
    """ 
    Get current working directory.
    
    Returns
    -------
    Path
    """
    
    return Path(__file__).cwd()

def main():
    # Input arguments
    inputs, outputs, subtitle_presets, overwrite = cli_args()
    
    
    for fl in inputs:
        # Prepare attachments folder path
        fl_attachments_folder = Path(fl.with_suffix('') + '_attachments')
        
        # Extract subs + fonts
        fl_attachments_folder = extract_subsnfonts(fl, fl_attachments_folder)
    
        # Read subs
        lines = read_subs(inputs[0])
        
        # Get Resolution/Format/Styles/Dialogues indices
        resx = get_lines_per_type(lines, ['PlayResX: '])
        resy = get_lines_per_type(lines, ['PlayResY: '])
        format_lines = get_lines_per_type(lines, ['Format: '])
        style_lines = get_lines_per_type(lines, ['Style: '])
        dialogue_lines = get_lines_per_type(lines, ['Dialogue: ','Comment: '])
        
        # Style names
        style_names = [(i,el[0],el[1][0]) for i,el in enumerate(style_lines)]
        
        # Style names from dialogue
        style_names_dialogue = list(set([el[1][3] for el in dialogue_lines]))
        
        # Keep the following styles which are in both defined in dialogue and styles
        keep_style_names = set(style_names_dialogue)-set(style_names)
        
        # Find them back in styles
        keep_style_lines_idx = [el[0] for el in style_names if el[2] in keep_style_names]
        remove_style_lines_idx = [el[0] for el in style_names if el[2] not in keep_style_names]
        
        # Kept styles used for restyling
        style_lines_kept = list(itemgetter(*keep_style_lines_idx)(style_lines))
        
        print(resx, resy)

if __name__ == "__main__":
    """ Main """

    # CWD
    wdir = cwd()
    
    # Attachments folder gene
    
    # Stop execution at keyboard input
    try:
        resl = main()
        #print(resl)
    except KeyboardInterrupt:
        print('\r\n\r\n> Execution cancelled by user')
        pass