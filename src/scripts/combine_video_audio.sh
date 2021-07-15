# $1: original_video path
# $2: transfer_video path
# $3: output_path

src/scripts/ffmpeg/bin/ffmpeg.exe -i $1 -i $2 -c copy -map 0:v:0 -map 1:a:0 -shortest $3