from types import SimpleNamespace

import click
import pytest

from ffconv.args import OutputPathChecker


def _single_file_input(tmp_path):
    input_file = tmp_path / "input.mkv"
    return [{"batch": 1, "input": {"given": str(input_file), "resolved": [input_file]}}]


def _directory_input(tmp_path, amount_of_files):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    files = [input_dir / f"ep{index:02}.mkv" for index in range(amount_of_files)]
    for file in files:
        file.touch()
    return [{"batch": 1, "input": {"given": str(input_dir), "resolved": files}}]


def _check_output(input_path, output_path):
    return OutputPathChecker()(
        SimpleNamespace(params={"input_path": input_path}),
        None,
        (str(output_path),),
    )


@pytest.mark.parametrize(
    "directory_name",
    [
        "This is a T.E.S.T. 1",
        "plain directory",
        "unsupported.mkv",
    ],
)
def test_output_path_checker_creates_directory(tmp_path, directory_name):
    output_path = tmp_path / directory_name

    result = _check_output(_single_file_input(tmp_path), output_path)

    assert output_path.is_dir()
    assert result[0]["output"]["resolved"] == output_path


@pytest.mark.parametrize("filename", ["foo.mp4", "foo.MP4", "foo.webm", "foo.avi"])
def test_output_path_checker_accepts_supported_output_file(tmp_path, filename):
    output_path = tmp_path / filename

    result = _check_output(_single_file_input(tmp_path), output_path)

    assert not output_path.exists()
    assert result[0]["output"]["resolved"] == output_path


def test_output_path_checker_rejects_output_file_with_missing_parent(tmp_path):
    output_path = tmp_path / "missing" / "foo.mp4"

    with pytest.raises(FileNotFoundError):
        _check_output(_single_file_input(tmp_path), output_path)


def test_output_path_checker_treats_existing_supported_suffix_directory_as_dir(
    tmp_path,
):
    output_path = tmp_path / "x.mp4"
    output_path.mkdir()

    result = _check_output(_single_file_input(tmp_path), output_path)

    assert output_path.is_dir()
    assert result[0]["output"]["resolved"] == output_path


@pytest.mark.parametrize("amount_of_files", [1, 3])
def test_output_path_checker_creates_directory_for_directory_input(
    tmp_path, amount_of_files
):
    output_path = tmp_path / "This is a T.E.S.T. 1"

    result = _check_output(_directory_input(tmp_path, amount_of_files), output_path)

    assert output_path.is_dir()
    assert result[0]["output"]["resolved"] == output_path


@pytest.mark.parametrize("amount_of_files", [1, 3])
def test_output_path_checker_rejects_output_file_for_directory_input(
    tmp_path, amount_of_files
):
    output_path = tmp_path / "foo.mp4"

    with pytest.raises(click.BadParameter):
        _check_output(_directory_input(tmp_path, amount_of_files), output_path)

    assert not output_path.exists()


def test_output_path_checker_rejects_output_file_for_multiple_input_files(tmp_path):
    files = [tmp_path / "ep01.mkv", tmp_path / "ep02.mkv"]
    input_path = [{"batch": 1, "input": {"given": str(files[0]), "resolved": files}}]

    with pytest.raises(click.BadParameter):
        _check_output(input_path, tmp_path / "foo.mp4")


def test_output_path_checker_existing_supported_suffix_dir_ok_for_directory_input(
    tmp_path,
):
    output_path = tmp_path / "x.mp4"
    output_path.mkdir()

    result = _check_output(_directory_input(tmp_path, 3), output_path)

    assert result[0]["output"]["resolved"] == output_path


def test_output_path_checker_broadcasts_single_output_per_batch(tmp_path):
    single_dir = tmp_path / "single"
    single_dir.mkdir()
    input_path = [
        *_single_file_input(single_dir),
        {**_directory_input(tmp_path, 2)[0], "batch": 2},
    ]
    output_path = tmp_path / "out"

    result = _check_output(input_path, output_path)

    assert output_path.is_dir()
    assert [batch["output"]["resolved"] for batch in result] == [output_path] * 2
