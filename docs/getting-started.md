## Requirements

- 🐋 [Docker](https://docs.docker.com/get-docker/)

## Pull image

```sh
docker pull ghcr.io/toshy/ffconv:latest
```

## Run container

### 🐋 Docker

Run with `docker`.

```sh
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v ${PWD}/input:/app/input \
  -v ${PWD}/output:/app/output \
  ghcr.io/toshy/ffconv:latest -h
```

### 🐳 Compose

Create a `compose.yaml` file.

```yaml
services:
  ffconv:
    image: ghcr.io/toshy/ffconv:latest
    volumes:
      - ./input:/app/input
      - ./output:/app/output
```

Run with `docker compose`.

```sh
docker compose run -u $(id -u):$(id -g) --rm ffconv -h
```

## Volumes

The following volume mounts are **required**: 

- `/app/input`
- `/app/output`

The following volume mounts are **optional**: 

- `/app/preset`
- `/app/fonts`


!!! tip
    Check the [presets](presets.md) section for more info about presets.

!!! tip

    Sometimes MKV files are missing embedded fonts, which can lead to incorrectly styled subtitles. One way to prevent this
    from happening, is to mount an additional (system-wide) fonts directory to `/app/fonts`. FFmpeg ([fontconfig](https://www.freedesktop.org/wiki/Software/fontconfig/)) will
    use that directory as a fallback in case an embedded font is missing.
    ```yaml
    # Mount local fonts directory
    ./fonts:/app/fonts:ro
    # Mount system-wide fonts directory
    /usr/share/fonts:/app/fonts:ro
    ```