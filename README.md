# 📺 FFconv

This repository contains several useful command-line scripts for hardcoding, restyling, and adding attachments to MKV
files in a (semi)-automatic fashion.

### FFconv

Tool for hardcoding subtitles into videos; converting MKV to web compatible MP4.

### MKVresort

Tool for reordering streams in a user-defined fashion.

### MKVrestyle

Tool for basic restyling of an embedded ASS file with a new user-defined font and styling.

### MKVrefont

Tool for adding attachments (subtitles, fonts) to existing MKV files.

## Installation

Install the required packages with `pip`:

```
pip3 install -r requirements.txt
```

## Usage

### FFconv

```shell
python ffconv.py -i "./input/" -o "./output/" -e "mp4"
```

### MKVresort

```shell
python mkvremux.py -i "input/file.mkv" -o "output" -s "preset/sort_preset.json"
```

### MKVrestyle

```shell
python mkvrestyle.py -i "./input/" -o "./output/" -sp "./preset/subtitle_preset.json"
```

### MKVrefont

```shell
python mkvattach.py -i "./input/myfile.mkv" -o "./output" -f "./input/fonts"
```