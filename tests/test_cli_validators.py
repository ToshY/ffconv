import pytest

from ffconv.cli import validate_stream_count, validate_stream_order
from ffconv.exception import StreamOrderError, StreamTypeMissingError

FILE_DETAILS = {"file_name": "test.mkv", "batch_name": "batch1"}


class TestValidateStreamOrder:
    def test_correct_order_passes(self):
        streams = {
            "video": {"count": 1},
            "audio": {"count": 1},
            "subtitles": {"count": 1},
        }
        validate_stream_order(streams, FILE_DETAILS)  # should not raise

    def test_audio_first_raises(self):
        streams = {
            "audio": {"count": 1},
            "video": {"count": 1},
            "subtitles": {"count": 1},
        }
        with pytest.raises(StreamOrderError):
            validate_stream_order(streams, FILE_DETAILS)

    def test_subtitles_before_audio_raises(self):
        streams = {
            "video": {"count": 1},
            "subtitles": {"count": 1},
            "audio": {"count": 1},
        }
        with pytest.raises(StreamOrderError):
            validate_stream_order(streams, FILE_DETAILS)

    def test_error_message_mentions_expected_and_actual_types(self):
        streams = {
            "audio": {"count": 1},
            "video": {"count": 1},
            "subtitles": {"count": 1},
        }
        with pytest.raises(StreamOrderError) as exc_info:
            validate_stream_order(streams, FILE_DETAILS)
        assert "video" in str(exc_info.value)
        assert "audio" in str(exc_info.value)


class TestValidateStreamCount:
    def test_all_streams_present_passes(self):
        streams = {
            "video": {"count": 1},
            "audio": {"count": 1},
            "subtitles": {"count": 1},
        }
        validate_stream_count(streams, FILE_DETAILS)  # should not raise

    def test_missing_video_raises(self):
        streams = {
            "audio": {"count": 1},
            "subtitles": {"count": 1},
        }
        with pytest.raises(StreamTypeMissingError):
            validate_stream_count(streams, FILE_DETAILS)

    def test_missing_audio_raises(self):
        streams = {
            "video": {"count": 1},
            "subtitles": {"count": 1},
        }
        with pytest.raises(StreamTypeMissingError):
            validate_stream_count(streams, FILE_DETAILS)

    def test_missing_subtitles_raises(self):
        streams = {
            "video": {"count": 1},
            "audio": {"count": 1},
        }
        with pytest.raises(StreamTypeMissingError):
            validate_stream_count(streams, FILE_DETAILS)

    def test_empty_streams_raises(self):
        with pytest.raises(StreamTypeMissingError):
            validate_stream_count({}, FILE_DETAILS)

    def test_error_message_mentions_missing_type(self):
        streams = {"video": {"count": 1}, "audio": {"count": 1}}
        with pytest.raises(StreamTypeMissingError) as exc_info:
            validate_stream_count(streams, FILE_DETAILS)
        assert "subtitles" in str(exc_info.value)

    def test_extra_stream_types_still_pass(self):
        streams = {
            "video": {"count": 1},
            "audio": {"count": 2},
            "subtitles": {"count": 3},
            "attachments": {"count": 1},
        }
        validate_stream_count(streams, FILE_DETAILS)  # should not raise
