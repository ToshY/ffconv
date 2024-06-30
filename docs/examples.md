# Examples

## Basic

Add your files to the input directory of the mounted container.

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest
```

By default, it will find all files from the `/app/input` directory (recursively) and write them to the `/app/output` directory. If
no presets are provided, it will automatically use the [`preset/video.json`](presets.md#default) and [`preset/audio.json`](presets.md#default_1).

## Specific file

Convert only a specific file and writing output to `/app/output` (default).

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest \
  -i "input/rick-astley-never-gonna-give-you-up.mkv"
```

## Single file with output subdirectory

Convert only a specific file and writing output to `/app/output/hits`.

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest \
  -i "input/rick-astley-never-gonna-give-you-up.mkv" \
  -o "output/hits"
```

## Specific subdirectory

Convert specific subdirectory and writing output to `/app/output/hits`.

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest \
  -i "input/hits" \
  -o "output/hits"
```

## Multiple inputs

Multiple input subdirectories and writing output to `/app/output` (default).

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest \
  -i "input/dir1" \
  -i "input/dir2" \
  -i "input/dir3" \
  -i "input/dir4" \
  -i "input/dir5"
```

## Multiple inputs and outputs

Multiple input subdirectories and writing output to specific output subdirectories respectively.

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest \
  -i "input/dir1" \
  -i "input/dir2" \
  -i "input/dir3" \
  -i "input/dir4" \
  -i "input/dir5" \
  -o "output/dir1" \
  -o "output/dir2" \
  -o "output/dir3" \
  -o "output/dir4" \
  -o "output/dir5"
```

## Multiple inputs, outputs and single video/audio preset

Multiple input subdirectories, with single video and audio preset, and writing output to specific output subdirectories respectively.

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest \
  -i "input/dir1" \
  -i "input/dir2" \
  -i "input/dir3" \
  -i "input/dir4" \
  -i "input/dir5" \
  -vp "preset/movie.json" \
  -ap "preset/audio-copy.json" \
  -o "output/dir1" \
  -o "output/dir2" \
  -o "output/dir3" \
  -o "output/dir4" \
  -o "output/dir5"
```

## Multiple inputs, outputs and presets

Multiple input subdirectories, with different presets, and writing output to specific output subdirectories respectively.

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/preset/video-custom.json:/app/preset/video-custom.json \
  -v $(pwd)/preset/audio-custom.json:/app/preset/audio-custom.json \
  ghcr.io/toshy/ffconv:latest \
  -i "input/dir1" \
  -i "input/dir2" \
  -i "input/dir3" \
  -i "input/dir4" \
  -i "input/dir5" \
  -vp "preset/video.json" \
  -vp "preset/movie.json" \
  -vp "preset/movie.json" \
  -vp "preset/video-custom.json" \
  -vp "preset/movie.json" \
  -ap "preset/audio.json" \
  -ap "preset/audio-copy.json" \
  -ap "preset/audio-copy.json" \
  -ap "preset/audio-custom.json" \
  -ap "preset/audio-copy.json" \
  -fp "preset/filter.json"
  -o "output/dir1" \
  -o "output/dir2" \
  -o "output/dir3" \
  -o "output/dir4" \
  -o "output/dir5"
```

## Automatic audio preset selection

You can provide the `--auto-audio-preset` flag to automatically let the tool decide what preset to use for audio streams.
This option overrides the `--audio-preset`/`-ap` option.

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ghcr.io/toshy/ffconv:latest \
  --auto-audio-preset
```

!!! note "Decision"

    If the input audio stream codec is of type `AAC`, use [`preset/audio-copy.json`](presets.md#default_1), else use [`preset/audio.json`](presets.md#default_1).