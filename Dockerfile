ARG PYTHON_IMAGE_VERSION=3.11

FROM python:${PYTHON_IMAGE_VERSION}-slim-bookworm AS base

LABEL maintainer="ToshY (github.com/ToshY)"

ENV PIP_ROOT_USER_ACTION ignore

WORKDIR /build

RUN <<EOT bash
  set -ex
  apt-get update
  apt install -y build-essential cmake wget
  wget -O /usr/share/keyrings/gpg-pub-moritzbunkus.gpg https://mkvtoolnix.download/gpg-pub-moritzbunkus.gpg
  echo "deb [signed-by=/usr/share/keyrings/gpg-pub-moritzbunkus.gpg] https://mkvtoolnix.download/debian/ bookworm main" > /etc/apt/sources.list.d/mkvtoolnix.download.list
  echo "deb-src [signed-by=/usr/share/keyrings/gpg-pub-moritzbunkus.gpg] https://mkvtoolnix.download/debian/ bookworm main" >> /etc/apt/sources.list.d/mkvtoolnix.download.list
  apt-get update
  apt install -y mkvtoolnix
  apt-get clean
  rm -rf /var/lib/apt/lists/*
  mkdir -p /var/cache/fontconfig
  chmod -R 777 /var/cache/fontconfig
EOT

COPY <<EOF /etc/fonts/conf.d/50-ffconv.conf
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
        <dir>/app/fonts</dir>
</fontconfig>
EOF

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade --force-reinstall 'setuptools>=65.5.1'

FROM base as ffmpeg

COPY --from=mwader/static-ffmpeg:7.0.1 /ffmpeg /usr/bin/
COPY --from=mwader/static-ffmpeg:7.0.1 /ffprobe /usr/bin/

FROM ffmpeg AS prod

COPY . .

RUN pip install .

WORKDIR /app

RUN <<EOT bash
  set -ex
  mkdir -p ./{input,output,preset,fonts}
  cp -r /build/preset ./
  rm -rf /build
EOT

ENTRYPOINT ["ffconv"]

FROM ffmpeg AS dev

WORKDIR /app

COPY requirements.dev.txt ./

RUN pip install --no-cache-dir -r requirements.dev.txt