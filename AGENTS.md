# FFconv — AI Agent Guide

CLI utility that hardcodes (burns-in) subtitles into video by converting MKV → MP4/webm/avi. Wraps `mkvmerge` (identify) and `ffmpeg` (convert). Python 3.11+, packaged as the `ffconv` console script (`setup.py` → `ffconv.cli:cli`).

## Architecture & data flow
The pipeline is a two-pass loop in `ffconv/cli.py:cli`, driven by Click:
1. **Identify pass** — `mkvmerge_identify_streams()` runs `mkvmerge --identify -F json`, groups tracks by `type` via `split_list_of_dicts_by_key`, then validates. Only the **first file of each batch** prompts the user for a stream map (`stream_user_input` + `rich.IntPrompt`); that map is reused for the whole batch.
2. **Convert pass** — `ffmpeg_convert_file()` builds an `ffmpeg -filter_complex "[0:v]subtitles='...':si=N"` command and burns subtitles.

Module roles: `args.py` = Click callback validators (turn CLI args into per-batch dicts), `helper.py` = pure data-shaping utils, `process.py` = subprocess runner, `exception.py` = typed errors, `table.py` = Rich stream-selection table.

## Project-specific conventions (read before editing)
- **Batch dicts**: every CLI option callback returns a list of `{"batch": N, <param.name>: value}` dicts. `combine_arguments_by_batch()` (helper.py) merges them by `batch` key into one dict per batch. Preserve this shape when adding options.
- **Arg count rule**: options accept either 1 value (broadcast to all inputs) or exactly one-per-input — see the repeated `amount_of_input_values != amount_of_current_param_values` check in `args.py`. Copy this pattern for new multi-value options.
- **Stream order is enforced**: source MKV must be ordered video → audio → subtitles (`validate_stream_order`), and all three types must exist (`validate_stream_count`) or it raises `StreamOrderError`/`StreamTypeMissingError`.
- **Subtitle index remap**: subtitle `si=` index is offset by the running video+audio count (`stream_map[...]["id"] - stream_sum_count`) because `-filter_complex subtitles` counts subtitle streams separately. Don't "simplify" this.
- **Presets are JSON dicts of raw ffmpeg flags** (`preset/video.json`, `audio.json`). Empty-string values are dropped by `remove_empty_dict_values`, then flattened to a flag list by `dict_to_list`. To add a flag, add a key like `"-crf": "18"`.
- **`--auto-audio-preset`** swaps `audio.json` → `audio-copy.json` when the source audio codec is `A_AAC` (avoids re-encoding). Logic lives in `AutoAudioFlagChecker` + top of `ffmpeg_convert_file`.
- **Filter presets** (`filter.json`) inject `before`/`after` scale filters around the subtitles filter for BT.709↔BT.601 color-space fixes.
- Subprocess calls go **only** through `ProcessCommand(logger).run(name, cmd)`; it maps `command[0]` (`mkvmerge`/`ffmpeg`) to a typed exception. Logging uses `loguru`.
- Filenames with quotes are stripped on-disk by `replace_conflicting_characters_in_filename` (renames the actual file) before ffmpeg sees them.

## Developer workflows (Docker + Task, no local Python needed)
Everything runs in containers via `Taskfile.yml`; there is **no local venv or pytest suite**.
- Build images: `task build` (dev + prod targets).
- Run the tool against `input/`→`output/`: `task prod -- -i input/foo.mkv -o output` (or `task dev -- <cli args>`; GPU: `task prod:gpu`).
- Lint/format/type-check (CI gates, all Docker-based): `task ruff`, `task black`, `task mypy` (use `:fix` variants to auto-fix). Line length limit is 88 (Black/Ruff defaults).
- Docs: `task docs:live` (Zensical dev server on :8001; config in `zensical.toml`).
- Open a shell: `task shell:dev`.

## Fonts & subtitle rendering (non-obvious)
- Burned-in subtitles/signs are rendered by **libass inside static-ffmpeg**, which relies on **fontconfig at runtime**. The `Dockerfile` installs a `/etc/fonts/conf.d/50-ffconv.conf` drop-in that registers `/app/fonts`; that drop-in is only honored because the root `/etc/fonts/fonts.conf` (from the `fontconfig-config` package) `<include>`s `conf.d`.
- **`fontconfig` must be installed explicitly** in the `Dockerfile` apt step. It is NOT pulled by `--no-install-recommends` — dropping it leaves a partial `/etc/fonts` tree, breaking font matching so signs fall back to the wrong font and no longer cover the original artwork (garbled/doubled signs). Keep `fontconfig` in the install list.
- Fonts a subtitle references (e.g. `\fnGentium Basic`) are resolved from: fonts **embedded in the MKV** (libass extracts attachments automatically) and the mounted `fonts/` → `/app/fonts` dir. If a sign renders wrong, first check the font is embedded/present — it is usually a font issue, not an ffmpeg/libass version regression.

## Releasing / version bumps
- The package version has a **single source of truth**: `VERSION` in `setup.py` (e.g. `VERSION = "3.0.0"`). Nothing else hardcodes it — the README release badge is a dynamic shields.io image, and `Taskfile.yml`'s `version: '3'` is the Taskfile schema, not the app.
- Pinned external tool versions live in the `Dockerfile`: `mwader/static-ffmpeg:<tag>` (both `/ffmpeg` and `/ffprobe` COPY lines) and `ARG PYTHON_IMAGE_VERSION`.
- Release flow = bump `setup.py` (+ any Dockerfile pins), commit, then push a matching `vX.Y.Z` git tag; the tag triggers the GitHub Actions publish to `ghcr.io/toshy/ffconv`. Verify the image still builds with `task build` before tagging.

## Key files
`ffconv/cli.py` (orchestration + Click options), `ffconv/args.py` (batch validators), `ffconv/helper.py`, `preset/*.json` (ffmpeg flag templates), `Dockerfile` (static-ffmpeg + mkvtoolnix + fontconfig `/app/fonts`), `Taskfile.yml` (all commands).


