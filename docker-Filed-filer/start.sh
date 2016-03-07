#!/bin/bash
while ! nc -z rabbitmq 5672; do sleep 3; done
python -u src/filer.py --logging_level DEBUG
