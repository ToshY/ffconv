## Usage

The following section shows the basic presets that are already available. You
can add your custom presets by mounting files to the `/app/preset` directory.

---

### 🐋 Docker

```shell
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v ${PWD}/input:/app/input \
  -v ${PWD}/output:/app/output \
  -v ${PWD}/preset/video-custom.json:/app/preset/video-custom.json \
  -v ${PWD}/preset/audio-custom.json:/app/preset/audio-custom.json \
  ghcr.io/toshy/ffconv:latest
```

### 🐳 Compose

```yaml
services:
  ffconv:
    image: ghcr.io/toshy/ffconv:latest
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./preset/video-custom.json:/app/preset/video-custom.json
      - ./preset/audio-custom.json:/app/preset/audio-custom.json
```

## Video

Argument: `--video-preset` / `-vp`.

---

### Default

???+ example "`video.json`"

    ```json
    {
        "-c:v": "libx264",
        "-s": "",
        "-r": "",
        "-pix_fmt": "yuv420p",
        "-crf": "18",
        "-b:v": "",
        "-minrate": "",
        "-maxrate": "",
        "-bufsize": "",
        "-preset": "slow",
        "-tune": "",
        "-profile:v": "high",
        "-level:v": "4.0"
    }
    ```

### Movie

???+ example "`movie.json`"

    ```json
    {
        "-c:v": "libx264",
        "-s": "",
        "-r": "",
        "-pix_fmt": "yuv420p",
        "-crf": "21",
        "-b:v": "",
        "-minrate": "",
        "-maxrate": "",
        "-bufsize": "",
        "-preset": "slow",
        "-tune": "",
        "-profile:v": "high",
        "-level:v": "4.0"
    }
    ```

### GPU
???+ example "`video-gpu.json`"

    If you want to leverage your NVIDIA GPU for encoding, you can use `h264_nvenc`.

    ```json
    {
        "-c:v": "h264_nvenc",
        "-s": "",
        "-r": "",
        "-pix_fmt": "yuv420p",
        "-cq": "20",
        "-qmin": "19",
        "-qmax": "21",
        "-preset": "slow",
        "-profile:v": "high",
        "-level:v": "4.0"
    }
    ```

    Please note that you should provide `--gpus` flag to the docker/compose command for this to work, e.g. `--gpus all`.

## Filters

Argument: `--filter-preset` / `-fp`.

---

In case you need more advanced video filters (e.g. changing color standard), you can
provide additional filters that will be added to the `filter_complex` statement in the FFmpeg command.

???+ example "`filter.json`"

    The following preset will convert the video from BT.709 to BT.601 color standard (`before`), add the subtitle, and convert the result back from BT.601 to BT.709 color standard (`after`).

    ```json
    {
        "before": "scale=in_color_matrix=bt709:out_color_matrix=bt601",
        "after": "scale=in_color_matrix=bt601:out_color_matrix=bt709"
    }
    ```

    The `-filter_complex` will look like this:

    ```shell
    -filter_complex scale=in_color_matrix=bt709:out_color_matrix=bt601,subtitles='/app/input/video.mkv':si=1,scale=in_color_matrix=bt601:out_color_matrix=bt709
    ```

## Audio

Argument: `--audio-preset` / `-ap`.

---

### Default

???+ example "`audio.json`"

    Use in cases the audio is not `AAC` (e.g. `FLAC`).

    ```json
    {
        "-c:a": "aac",
        "-strict": "2",
        "-ab": "128k",
        "-ac": "2"
    }
    ```

### Copy

???+ example "`audio-copy.json`"

    Use in cases the audio is already `AAC`.

    ```json
    {
        "-c:a": "copy"
    }
    ```