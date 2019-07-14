#!/bin/bash
set -x


time fortune
time ./fim.py
time pipenv run python fim.py
time docker run -v /tmp/fim_test.db:/var/fim/fortune.db fim:latest
