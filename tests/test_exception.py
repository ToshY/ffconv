import pytest

from ffconv.exception import (
    FFmpegError,
    MKVmergeError,
    ProcessError,
    StreamOrderError,
    StreamTypeMissingError,
)

FILE_DETAILS = {"file_name": "test.mkv", "batch_name": "batch1"}


class TestMKVmergeError:
    def test_message_contains_exit_code(self):
        err = MKVmergeError("something went wrong", 1)
        assert "1" in str(err)

    def test_message_contains_error_text(self):
        err = MKVmergeError("something went wrong", 1)
        assert "something went wrong" in str(err)

    def test_exit_code_stored(self):
        err = MKVmergeError("error", 2)
        assert err.exit_code == 2

    def test_is_exception(self):
        with pytest.raises(MKVmergeError):
            raise MKVmergeError("error", 1)

    def test_is_subclass_of_exception(self):
        assert issubclass(MKVmergeError, Exception)


class TestFFmpegError:
    def test_message_contains_exit_code(self):
        err = FFmpegError("encode failed", 1)
        assert "1" in str(err)

    def test_message_contains_error_text(self):
        err = FFmpegError("encode failed", 1)
        assert "encode failed" in str(err)

    def test_exit_code_stored(self):
        err = FFmpegError("error", 127)
        assert err.exit_code == 127

    def test_is_subclass_of_exception(self):
        assert issubclass(FFmpegError, Exception)


class TestProcessError:
    def test_message_contains_exit_code(self):
        err = ProcessError("unknown failure", 255)
        assert "255" in str(err)

    def test_message_contains_error_text(self):
        err = ProcessError("unknown failure", 255)
        assert "unknown failure" in str(err)

    def test_exit_code_stored(self):
        err = ProcessError("error", 255)
        assert err.exit_code == 255

    def test_is_subclass_of_exception(self):
        assert issubclass(ProcessError, Exception)


class TestStreamOrderError:
    def test_message_contains_expected_stream_type(self):
        err = StreamOrderError("video", 0, "audio", FILE_DETAILS)
        assert "video" in str(err)

    def test_message_contains_actual_stream_type(self):
        err = StreamOrderError("video", 0, "audio", FILE_DETAILS)
        assert "audio" in str(err)

    def test_message_contains_index(self):
        err = StreamOrderError("video", 0, "audio", FILE_DETAILS)
        assert "0" in str(err)

    def test_message_contains_file_name(self):
        err = StreamOrderError("video", 0, "audio", FILE_DETAILS)
        assert "test.mkv" in str(err)

    def test_message_contains_batch_name(self):
        err = StreamOrderError("video", 0, "audio", FILE_DETAILS)
        assert "batch1" in str(err)

    def test_is_subclass_of_exception(self):
        assert issubclass(StreamOrderError, Exception)


class TestStreamTypeMissingError:
    def test_message_contains_stream_type(self):
        err = StreamTypeMissingError("subtitles", FILE_DETAILS)
        assert "subtitles" in str(err)

    def test_message_contains_file_name(self):
        err = StreamTypeMissingError("audio", FILE_DETAILS)
        assert "test.mkv" in str(err)

    def test_message_contains_batch_name(self):
        err = StreamTypeMissingError("video", FILE_DETAILS)
        assert "batch1" in str(err)

    def test_is_subclass_of_exception(self):
        assert issubclass(StreamTypeMissingError, Exception)
