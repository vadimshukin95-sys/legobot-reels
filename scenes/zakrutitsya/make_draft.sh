#!/bin/bash
# Черновик: кадры состояний (st/) -> кадры ролика (reel/) -> MP4 со звуком
set -e
cd "$(dirname "$0")"
python3 audio_z.py audio.wav
python3 overlay_z.py reel st reel
ffmpeg -y -hide_banner -loglevel error -framerate 30 -i reel/o%04d.png -i audio.wav \
  -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k \
  -af loudnorm=I=-14:TP=-1.5:LRA=11 -shortest -movflags +faststart "${1:-zakrutitsya_draft.mp4}"
