#!/bin/bash

# Go to the project directory (replace with your absolute path)
cd ~/src/snowbearGenerator

# Activate virtual environment
source venv/bin/activate
set -a
source .env
set +a

# Add --gif once every 7 days. The time of the last successful GIF run is kept
# in a stamp file, so a missed or failed run makes the GIF on the next one.
GIF_STAMP=.last_gif_run
GIF_INTERVAL_DAYS=7
now=$(date +%s)
last=$(cat "$GIF_STAMP" 2>/dev/null || echo 0)
# Round to whole days so a run a few minutes earlier than last week's still counts.
days_since=$(( (now - last + 43200) / 86400 ))

gif_flag=""
if [ "$days_since" -ge "$GIF_INTERVAL_DAYS" ]; then
    gif_flag="--gif"
    echo "Last GIF run was $days_since day(s) ago; generating a GIF today"
fi

# Run the script
python icebear-gen-image-assisted.py --env .env $gif_flag
status=$?

if [ -n "$gif_flag" ] && [ "$status" -eq 0 ]; then
    echo "$now" > "$GIF_STAMP"
fi

# Deactivate virtual environment
deactivate
exit $status
