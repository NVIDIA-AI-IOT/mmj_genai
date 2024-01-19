#!/bin/bash
python3 /mmj_genai/main.py $STREAM_INPUT --stream_output $RTSP_OUT --redis_host $REDIS_HOST --redis_port $REDIS_PORT --flask_port $FLASK_PORT
