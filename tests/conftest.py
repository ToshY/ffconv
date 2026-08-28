import shutil
import subprocess

import pytest

from ffconv.cli import mkvmerge_identify_streams


def _binaries_available():
    return (
        shutil.which("ffmpeg") is not None
        and shutil.which("ffprobe") is not None
        and shutil.which("mkvmerge") is not None
    )


@pytest.fixture(scope="session")
def test_mkv(tmp_path_factory):
    if not _binaries_available():
        pytest.skip("ffmpeg and mkvmerge required")

    tmp = tmp_path_factory.mktemp("media")

    srt_path = tmp / "sub.srt"
    srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest subtitle\n\n")

    mkv_path = tmp / "test.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=64x64:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-i",
            str(srt_path),
            "-t",
            "2",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "2:s",
            "-c:v",
            "libx264",
            "-crf",
            "51",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-ab",
            "32k",
            "-c:s",
            "srt",
            str(mkv_path),
        ],
        check=True,
        capture_output=True,
    )

    return mkv_path


@pytest.fixture(scope="session")
def stream_mapping(test_mkv):
    _, mapping = mkvmerge_identify_streams(
        test_mkv, total_items=1, item_index=0, batch_index=1, batch_name="test"
    )
    return mapping


@pytest.fixture(scope="session")
def test_mkv_ass(tmp_path_factory):
    """MKV with ASS subtitles — the most common real-world subtitle format."""
    if not _binaries_available():
        pytest.skip("ffmpeg, ffprobe and mkvmerge required")

    tmp = tmp_path_factory.mktemp("media_ass")

    ass_path = tmp / "sub.ass"
    ass_path.write_text(
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 64\n"
        "PlayResY: 64\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,"
        " Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline,"
        " Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,12,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Test subtitle\n"
    )

    mkv_path = tmp / "test_ass.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=64x64:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-i",
            str(ass_path),
            "-t",
            "2",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "2:s",
            "-c:v",
            "libx264",
            "-crf",
            "51",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-ab",
            "32k",
            "-c:s",
            "ass",
            str(mkv_path),
        ],
        check=True,
        capture_output=True,
    )

    return mkv_path


@pytest.fixture(scope="session")
def test_mkv_vorbis(tmp_path_factory):
    """MKV with Vorbis audio — exercises the auto-preset default (re-encode) path."""
    if not _binaries_available():
        pytest.skip("ffmpeg, ffprobe and mkvmerge required")

    tmp = tmp_path_factory.mktemp("media_vorbis")

    srt_path = tmp / "sub.srt"
    srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest subtitle\n\n")

    mkv_path = tmp / "test_vorbis.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=64x64:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-i",
            str(srt_path),
            "-t",
            "2",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "2:s",
            "-c:v",
            "libx264",
            "-crf",
            "51",
            "-preset",
            "ultrafast",
            "-c:a",
            "libvorbis",
            "-c:s",
            "srt",
            str(mkv_path),
        ],
        check=True,
        capture_output=True,
    )

    return mkv_path
