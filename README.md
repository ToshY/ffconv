<h1 align="center"> 📺 FFconv </h1>

<div align="center">
    <img src="https://img.shields.io/github/v/release/toshy/ffconv?label=Release&sort=semver" alt="Current bundle version" />
    <img src="https://img.shields.io/github/actions/workflow/status/toshy/ffconv/codestyle.yml?branch=main&label=Ruff" alt="Ruff">
    <img src="https://img.shields.io/github/actions/workflow/status/toshy/ffconv/statictyping.yml?branch=main&label=Mypy" alt="Mypy">
    <img src="https://img.shields.io/github/actions/workflow/status/toshy/ffconv/security.yml?branch=main&label=Security%20check" alt="Security check" />
    <br /><br />
    <div>A command-line utility for hardcoding subtitles into videos by converting MKV to MP4.</div>
</div>

## 📝 Quickstart

A command-line utility for hardcoding subtitles into videos by converting MKV to MP4.

## 🧰 Requirements

* 🐋 [Docker](https://docs.docker.com/get-docker/)

## 🎬 Usage

FFconv requires 2 volumes to be mounted: `/app/input` and `/app/output`.

### 🐋 Docker

```shell
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
      - ./input:/input
      - ./output:/output
```

Then run it.

```shell
docker compose run -u $(id -u):$(id -g) --rm ffconv -h
```

> [!TIP]
> You can add additional JSON presets by mounting the files to the preset directory:
> ```shell
> ./preset/custom.json:/app/preset/custom.json
> ```

> [!TIP]
> Sometimes MKV files are missing embedded fonts, which can lead to incorrectly styled subtitles. In order to remediate this
> problem, you can mount your own fonts directory to `/usr/local/share/fonts`.
> ```yaml
> # Mount local fonts directory
> ./fonts:/usr/local/share/fonts:ro
> # Mount system-wide fonts directory
> /usr/share/fonts:/usr/local/share/fonts:ro
> ```

## 🛠️ Contribute

### Requirements

* ☑️ [Pre-commit](https://pre-commit.com/#installation).
* 🐋 [Docker Compose V2](https://docs.docker.com/compose/install/)
* 📋 [Task 3.37+](https://taskfile.dev/installation/)

### Pre-commit

Setting up `pre-commit` code style & quality checks for local development.

```shell
pre-commit install
```

## ❕ License

This repository comes with a [MIT license](./LICENSE).
