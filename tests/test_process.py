from unittest.mock import MagicMock, patch

import pytest
from loguru import logger

from ffconv.exception import FFmpegError, MKVmergeError, ProcessError
from ffconv.process import ProcessCommand


def make_completed_process(returncode, stdout=b"", stderr=b""):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestProcessCommand:
    def setup_method(self):
        self.process = ProcessCommand(logger)

    def test_success_returns_completed_process(self):
        mock_result = make_completed_process(0, stdout=b'{"tracks": []}')
        with patch("subprocess.run", return_value=mock_result):
            result = self.process.run(
                "MKVmerge identify", ["mkvmerge", "--identify", "file.mkv"]
            )
        assert result is mock_result

    def test_calls_subprocess_with_correct_args(self):
        mock_result = make_completed_process(0)
        command = ["ffmpeg", "-version"]
        with patch("subprocess.run", return_value=mock_result) as mock_sp:
            self.process.run("Test", command)
        mock_sp.assert_called_once_with(command, capture_output=True, check=False)

    def test_mkvmerge_failure_raises_mkvmerge_error(self):
        mock_result = make_completed_process(1, stderr=b"file not found")
        with patch("subprocess.run", return_value=mock_result), pytest.raises(
            MKVmergeError
        ):
            self.process.run(
                "MKVmerge identify", ["mkvmerge", "--identify", "missing.mkv"]
            )

    def test_ffmpeg_failure_raises_ffmpeg_error(self):
        mock_result = make_completed_process(1, stderr=b"Invalid codec")
        with patch("subprocess.run", return_value=mock_result), pytest.raises(
            FFmpegError
        ):
            self.process.run(
                "FFmpeg convert", ["ffmpeg", "-i", "input.mkv", "output.mp4"]
            )

    def test_unknown_command_failure_raises_process_error(self):
        mock_result = make_completed_process(1, stderr=b"some error")
        with patch("subprocess.run", return_value=mock_result), pytest.raises(
            ProcessError
        ):
            self.process.run("Custom", ["custom-tool", "arg"])

    def test_mkvmerge_error_contains_stderr_message(self):
        mock_result = make_completed_process(1, stderr=b"No such file")
        with patch("subprocess.run", return_value=mock_result), pytest.raises(
            MKVmergeError
        ) as exc_info:
            self.process.run("MKVmerge identify", ["mkvmerge", "--identify", "x.mkv"])
        assert "No such file" in str(exc_info.value)

    def test_ffmpeg_error_stores_exit_code(self):
        mock_result = make_completed_process(255, stderr=b"error")
        with patch("subprocess.run", return_value=mock_result), pytest.raises(
            FFmpegError
        ) as exc_info:
            self.process.run("FFmpeg convert", ["ffmpeg", "-i", "x.mkv", "out.mp4"])
        assert exc_info.value.exit_code == 255

    def test_nonzero_mkvmerge_exit_code_raises(self):
        for code in [1, 2, 127]:
            mock_result = make_completed_process(code, stderr=b"error")
            with patch("subprocess.run", return_value=mock_result), pytest.raises(
                MKVmergeError
            ):
                self.process.run("MKVmerge", ["mkvmerge", "file.mkv"])
