<h1 align="center"> 📺 FFconv </h1>

<div align="center">
    <img src="https://img.shields.io/github/v/release/toshy/ffconv?label=Release&sort=semver" alt="Current bundle version" />
    <img src="https://img.shields.io/github/actions/workflow/status/toshy/ffconv/codestyle.yml?branch=master&label=Black" alt="Black">
    <img src="https://img.shields.io/github/actions/workflow/status/toshy/ffconv/codequality.yml?branch=master&label=Ruff" alt="Ruff">
    <img src="https://img.shields.io/github/actions/workflow/status/toshy/ffconv/statictyping.yml?branch=master&label=Mypy" alt="Mypy">
    <img src="https://img.shields.io/github/actions/workflow/status/toshy/ffconv/security.yml?branch=master&label=Security%20check" alt="Security check" />
    <br /><br />
    <div>A command-line utility for hardcoding subtitles into videos by converting MKV to MP4.</div>
</div>

## 📝 Quickstart

```sh
docker run -it --rm \
  -u $(id -u):$(id -g) \
  -v ${PWD}/input:/app/input \
  -v ${PWD}/output:/app/output \
  ghcr.io/toshy/ffconv:latest
```

## 📜 Documentation

The documentation is available at [https://toshy.github.io/ffconv](https://toshy.github.io/ffconv).

## 🛠️ Contribute

### Requirements

* ☑️ [Pre-commit](https://pre-commit.com/#installation).
* 🐋 [Docker Compose V2](https://docs.docker.com/compose/install/)
* 📋 [Task 3.37+](https://taskfile.dev/installation/)

## ❕ License

This repository comes with a [MIT license](./LICENSE).
