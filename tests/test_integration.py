import json
import re
import shutil
import subprocess

import pytest

from ffconv.cli import ffmpeg_convert_file, mkvmerge_identify_streams

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None
    or shutil.which("mkvmerge") is None,
    reason="ffmpeg, ffprobe and mkvmerge required",
)

FAST_VIDEO_PRESET = {
    "-c:v": "libx264",
    "-crf": "51",
    "-preset": "ultrafast",
    "-pix_fmt": "yuv420p",
}
FAST_AUDIO_PRESET = {"-c:a": "aac", "-ab": "32k"}


def _ffprobe_tags(path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)["format"].get("tags", {})


def _convert(
    test_mkv,
    stream_mapping,
    output_path,
    extension="mp4",
    filter_preset=None,
    auto_audio_preset=False,
):
    ffmpeg_convert_file(
        input_file=test_mkv,
        output_path=output_path,
        output_extension=extension,
        stream_mapping=stream_mapping,
        video_preset=FAST_VIDEO_PRESET,
        audio_preset=FAST_AUDIO_PRESET,
        filter_preset=filter_preset,
        total_items=1,
        item_index=0,
        batch_index=1,
        batch_name="test",
        auto_audio_preset=auto_audio_preset,
    )


class TestMkvmergeIdentifyStreams:
    def test_detects_all_three_stream_types(self, test_mkv):
        streams, _ = mkvmerge_identify_streams(
            test_mkv, total_items=1, item_index=0, batch_index=1, batch_name="test"
        )
        assert "video" in streams
        assert "audio" in streams
        assert "subtitles" in streams

    def test_each_type_has_one_stream(self, test_mkv):
        streams, _ = mkvmerge_identify_streams(
            test_mkv, total_items=1, item_index=0, batch_index=1, batch_name="test"
        )
        assert streams["video"]["count"] == 1
        assert streams["audio"]["count"] == 1
        assert streams["subtitles"]["count"] == 1

    def test_mapping_returned_for_first_item(self, test_mkv):
        _, mapping = mkvmerge_identify_streams(
            test_mkv, total_items=2, item_index=0, batch_index=1, batch_name="test"
        )
        assert mapping is not None
        assert set(mapping.keys()) == {"video", "audio", "subtitles"}

    def test_no_mapping_for_subsequent_items(self, test_mkv):
        _, mapping = mkvmerge_identify_streams(
            test_mkv, total_items=2, item_index=1, batch_index=1, batch_name="test"
        )
        assert mapping is None

    def test_subtitle_id_remapped_to_stream_index(self, stream_mapping):
        # Subtitle id must be the subtitle-stream index (si=), not the global track id.
        # With 1 video + 1 audio track before it, the global id is 2, remapped to 0.
        assert stream_mapping["subtitles"]["id"] == 0

    def test_audio_codec_id_present(self, stream_mapping):
        assert "codec_id" in stream_mapping["audio"]["properties"]
        assert stream_mapping["audio"]["properties"]["codec_id"] == "A_AAC"


class TestFfmpegConvertFile:
    def test_output_file_created(self, test_mkv, stream_mapping, tmp_path):
        _convert(test_mkv, stream_mapping, tmp_path)
        assert (tmp_path / "test.mp4").exists()

    def test_output_file_is_not_empty(self, test_mkv, stream_mapping, tmp_path):
        _convert(test_mkv, stream_mapping, tmp_path)
        assert (tmp_path / "test.mp4").stat().st_size > 0

    def test_encoded_on_comment_present(self, test_mkv, stream_mapping, tmp_path):
        _convert(test_mkv, stream_mapping, tmp_path)
        tags = _ffprobe_tags(tmp_path / "test.mp4")
        assert tags.get("comment", "").startswith("Encoded on ")

    def test_encoded_on_date_format(self, test_mkv, stream_mapping, tmp_path):
        _convert(test_mkv, stream_mapping, tmp_path)
        tags = _ffprobe_tags(tmp_path / "test.mp4")
        assert re.match(
            r"Encoded on \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", tags.get("comment", "")
        )

    def test_title_metadata_matches_filename_stem(
        self, test_mkv, stream_mapping, tmp_path
    ):
        _convert(test_mkv, stream_mapping, tmp_path)
        tags = _ffprobe_tags(tmp_path / "test.mp4")
        assert tags.get("title") == test_mkv.stem

    def test_extension_with_leading_dot(self, test_mkv, stream_mapping, tmp_path):
        _convert(test_mkv, stream_mapping, tmp_path, extension=".mp4")
        assert (tmp_path / "test.mp4").exists()

    def test_explicit_output_file_path(self, test_mkv, stream_mapping, tmp_path):
        output_file = tmp_path / "custom_name.mp4"
        _convert(test_mkv, stream_mapping, output_file)
        assert output_file.exists()

    def test_filter_preset_before(self, test_mkv, stream_mapping, tmp_path):
        filter_preset = {"before": "scale=in_color_matrix=bt709:out_color_matrix=bt601"}
        _convert(test_mkv, stream_mapping, tmp_path, filter_preset=filter_preset)
        assert (tmp_path / "test.mp4").exists()

    def test_filter_preset_after(self, test_mkv, stream_mapping, tmp_path):
        filter_preset = {"after": "scale=in_color_matrix=bt601:out_color_matrix=bt709"}
        _convert(test_mkv, stream_mapping, tmp_path, filter_preset=filter_preset)
        assert (tmp_path / "test.mp4").exists()

    def test_filter_preset_before_and_after(self, test_mkv, stream_mapping, tmp_path):
        filter_preset = {
            "before": "scale=in_color_matrix=bt709:out_color_matrix=bt601",
            "after": "scale=in_color_matrix=bt601:out_color_matrix=bt709",
        }
        _convert(test_mkv, stream_mapping, tmp_path, filter_preset=filter_preset)
        assert (tmp_path / "test.mp4").exists()

    def test_auto_audio_aac_selects_copy_preset(
        self, test_mkv, stream_mapping, tmp_path
    ):
        auto_preset = {
            "default": {"-c:a": "aac", "-ab": "32k"},
            "copy": {"-c:a": "copy"},
        }
        _convert(test_mkv, stream_mapping, tmp_path, auto_audio_preset=auto_preset)
        assert (tmp_path / "test.mp4").exists()


def _ffprobe_audio_codec(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            str(path),
        ],
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)["streams"][0]["codec_name"]


class TestASSSubtitles:
    def test_identifies_subtitle_stream(self, test_mkv_ass):
        streams, _ = mkvmerge_identify_streams(
            test_mkv_ass, total_items=1, item_index=0, batch_index=1, batch_name="test"
        )
        assert "subtitles" in streams
        assert streams["subtitles"]["count"] == 1

    def test_ass_subtitle_codec_id(self, test_mkv_ass):
        streams, _ = mkvmerge_identify_streams(
            test_mkv_ass, total_items=1, item_index=0, batch_index=1, batch_name="test"
        )
        codec_id = streams["subtitles"]["streams"][0]["properties"]["codec_id"]
        assert codec_id == "S_TEXT/ASS"

    def test_converts_to_mp4(self, test_mkv_ass, tmp_path):
        _, mapping = mkvmerge_identify_streams(
            test_mkv_ass, total_items=1, item_index=0, batch_index=1, batch_name="test"
        )
        _convert(test_mkv_ass, mapping, tmp_path)
        assert (tmp_path / "test_ass.mp4").exists()
        assert (tmp_path / "test_ass.mp4").stat().st_size > 0

    def test_encoded_on_metadata(self, test_mkv_ass, tmp_path):
        _, mapping = mkvmerge_identify_streams(
            test_mkv_ass, total_items=1, item_index=0, batch_index=1, batch_name="test"
        )
        _convert(test_mkv_ass, mapping, tmp_path)
        tags = _ffprobe_tags(tmp_path / "test_ass.mp4")
        assert tags.get("comment", "").startswith("Encoded on ")


class TestNonAACAudioAutoPreset:
    def test_vorbis_codec_id(self, test_mkv_vorbis):
        _, mapping = mkvmerge_identify_streams(
            test_mkv_vorbis,
            total_items=1,
            item_index=0,
            batch_index=1,
            batch_name="test",
        )
        assert mapping["audio"]["properties"]["codec_id"] == "A_VORBIS"

    def test_non_aac_selects_default_preset(self, test_mkv_vorbis, tmp_path):
        _, mapping = mkvmerge_identify_streams(
            test_mkv_vorbis,
            total_items=1,
            item_index=0,
            batch_index=1,
            batch_name="test",
        )
        auto_preset = {
            "default": {"-c:a": "aac", "-ab": "32k"},
            "copy": {"-c:a": "copy"},
        }
        _convert(test_mkv_vorbis, mapping, tmp_path, auto_audio_preset=auto_preset)
        # Default preset re-encodes to AAC; copy would have left it as Vorbis
        assert _ffprobe_audio_codec(tmp_path / "test_vorbis.mp4") == "aac"

    def test_non_aac_copy_would_fail_so_default_is_used(
        self, test_mkv_vorbis, tmp_path
    ):
        # Confirm the output file is produced successfully with the default preset
        _, mapping = mkvmerge_identify_streams(
            test_mkv_vorbis,
            total_items=1,
            item_index=0,
            batch_index=1,
            batch_name="test",
        )
        auto_preset = {
            "default": {"-c:a": "aac", "-ab": "32k"},
            "copy": {"-c:a": "copy"},
        }
        _convert(test_mkv_vorbis, mapping, tmp_path, auto_audio_preset=auto_preset)
        assert (tmp_path / "test_vorbis.mp4").exists()
