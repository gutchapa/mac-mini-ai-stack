#!/bin/bash
/home/dell/llama.cpp/build/bin/llama-cli -m /home/dell/models/phi3-mini-q3.gguf -p "$1" -n 200 --threads 4 --no-display-prompt
