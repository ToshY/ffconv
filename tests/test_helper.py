import json

from ffconv.helper import (
    combine_arguments_by_batch,
    dict_to_list,
    files_in_dir,
    preprocess_streams,
    read_json,
    remove_empty_dict_values,
    replace_conflicting_characters_in_filename,
    split_list_of_dicts_by_key,
)


class TestRemoveEmptyDictValues:
    def test_removes_none_values(self):
        assert remove_empty_dict_values({"a": 1, "b": None}) == {"a": 1}

    def test_removes_empty_string(self):
        assert remove_empty_dict_values({"a": "hello", "b": ""}) == {"a": "hello"}

    def test_removes_empty_list(self):
        assert remove_empty_dict_values({"a": [1], "b": []}) == {"a": [1]}

    def test_empty_dict(self):
        assert remove_empty_dict_values({}) == {}

    def test_all_values_present(self):
        assert remove_empty_dict_values({"a": 1, "b": "x"}) == {"a": 1, "b": "x"}

    def test_removes_zero(self):
        assert remove_empty_dict_values({"a": 1, "b": 0}) == {"a": 1}


class TestDictToList:
    def test_single_pair(self):
        assert dict_to_list({"-c:v": "libx264"}) == ["-c:v", "libx264"]

    def test_multiple_pairs(self):
        result = dict_to_list({"-c:v": "libx264", "-crf": "18"})
        assert result == ["-c:v", "libx264", "-crf", "18"]

    def test_three_pairs(self):
        result = dict_to_list({"-c:v": "libx265", "-crf": "22", "-preset": "slow"})
        assert result == ["-c:v", "libx265", "-crf", "22", "-preset", "slow"]


class TestSplitListOfDictsByKey:
    def test_single_type(self):
        tracks = [{"type": "video", "id": 0}, {"type": "video", "id": 1}]
        result, keys = split_list_of_dicts_by_key(tracks, "type")
        assert keys == ["video"]
        assert result == [[{"type": "video", "id": 0}, {"type": "video", "id": 1}]]

    def test_multiple_types(self):
        tracks = [
            {"type": "video", "id": 0},
            {"type": "audio", "id": 1},
            {"type": "subtitles", "id": 2},
        ]
        result, keys = split_list_of_dicts_by_key(tracks, "type")
        assert keys == ["video", "audio", "subtitles"]
        assert len(result) == 3
        assert result[0] == [{"type": "video", "id": 0}]
        assert result[1] == [{"type": "audio", "id": 1}]
        assert result[2] == [{"type": "subtitles", "id": 2}]

    def test_preserves_first_seen_order(self):
        tracks = [{"type": "audio", "id": 0}, {"type": "video", "id": 1}]
        _, keys = split_list_of_dicts_by_key(tracks, "type")
        assert keys == ["audio", "video"]

    def test_groups_same_type_together(self):
        tracks = [
            {"type": "audio", "id": 0},
            {"type": "audio", "id": 1},
            {"type": "video", "id": 2},
        ]
        result, keys = split_list_of_dicts_by_key(tracks, "type")
        assert keys == ["audio", "video"]
        assert len(result[0]) == 2

    def test_default_key_is_codec_type(self):
        tracks = [{"codec_type": "video"}, {"codec_type": "audio"}]
        _result, keys = split_list_of_dicts_by_key(tracks)
        assert keys == ["video", "audio"]


class TestCombineArgumentsByBatch:
    def test_single_batch(self):
        inputs = [{"batch": 1, "input": "a.mkv"}]
        outputs = [{"batch": 1, "output": "a.mp4"}]
        result = combine_arguments_by_batch(inputs, outputs)
        assert result == [{"batch": 1, "input": "a.mkv", "output": "a.mp4"}]

    def test_multiple_batches(self):
        inputs = [{"batch": 1, "input": "a.mkv"}, {"batch": 2, "input": "b.mkv"}]
        outputs = [{"batch": 1, "output": "a.mp4"}, {"batch": 2, "output": "b.mp4"}]
        result = combine_arguments_by_batch(inputs, outputs)
        assert len(result) == 2
        assert result[0] == {"batch": 1, "input": "a.mkv", "output": "a.mp4"}
        assert result[1] == {"batch": 2, "input": "b.mkv", "output": "b.mp4"}

    def test_later_list_overwrites_shared_key(self):
        a = [{"batch": 1, "value": "first"}]
        b = [{"batch": 1, "value": "second"}]
        result = combine_arguments_by_batch(a, b)
        assert result[0]["value"] == "second"


class TestPreprocessStreams:
    def test_indexes_by_id(self):
        streams = [
            {"id": 0, "properties": {"codec_id": "A_AAC"}},
            {"id": 1, "properties": {"codec_id": "A_AC3"}},
        ]
        result = preprocess_streams(streams)
        assert result[0] == streams[0]
        assert result[1] == streams[1]

    def test_returns_dict(self):
        streams = [{"id": 5, "properties": {}}]
        result = preprocess_streams(streams)
        assert isinstance(result, dict)
        assert 5 in result

    def test_empty_list(self):
        assert preprocess_streams([]) == {}


class TestFilesInDir:
    def test_finds_mkv_files(self, tmp_path):
        (tmp_path / "video.mkv").touch()
        (tmp_path / "other.mp4").touch()
        result = files_in_dir(tmp_path)
        assert len(result) == 1
        assert result[0].name == "video.mkv"

    def test_custom_file_type(self, tmp_path):
        (tmp_path / "video.mkv").touch()
        (tmp_path / "clip.mp4").touch()
        result = files_in_dir(tmp_path, ["*.mp4"])
        assert len(result) == 1
        assert result[0].name == "clip.mp4"

    def test_empty_directory(self, tmp_path):
        result = files_in_dir(tmp_path)
        assert result == []

    def test_case_insensitive_match(self, tmp_path):
        (tmp_path / "video.MKV").touch()
        result = files_in_dir(tmp_path)
        assert len(result) == 1

    def test_finds_files_recursively(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.mkv").touch()
        result = files_in_dir(tmp_path)
        assert len(result) == 1
        assert result[0].name == "deep.mkv"

    def test_multiple_mkv_files(self, tmp_path):
        (tmp_path / "a.mkv").touch()
        (tmp_path / "b.mkv").touch()
        result = files_in_dir(tmp_path)
        assert len(result) == 2


class TestReadJson:
    def test_reads_valid_json(self, tmp_path):
        data = {"key": "value", "number": 42}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data))
        assert read_json(json_file) == data

    def test_reads_nested_json(self, tmp_path):
        data = {"video": {"-c:v": "libx264", "-crf": "18"}}
        json_file = tmp_path / "preset.json"
        json_file.write_text(json.dumps(data))
        assert read_json(json_file) == data


class TestReplaceConflictingCharactersInFilename:
    def test_removes_single_quotes(self, tmp_path):
        original = tmp_path / "video's.mkv"
        original.touch()
        result = replace_conflicting_characters_in_filename(original)
        assert result.name == "videos.mkv"
        assert result.exists()
        assert not original.exists()

    def test_removes_double_quotes(self, tmp_path):
        original = tmp_path / 'video"test".mkv'
        original.touch()
        result = replace_conflicting_characters_in_filename(original)
        assert result.name == "videotest.mkv"
        assert result.exists()

    def test_no_conflicting_characters(self, tmp_path):
        original = tmp_path / "clean_video.mkv"
        original.touch()
        result = replace_conflicting_characters_in_filename(original)
        assert result.name == "clean_video.mkv"
        assert result.exists()

    def test_returns_path_object(self, tmp_path):
        original = tmp_path / "video.mkv"
        original.touch()
        result = replace_conflicting_characters_in_filename(original)
        assert isinstance(result, type(original))
