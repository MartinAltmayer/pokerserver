#!/usr/bin/env bash

VIRTUAL_ENVIRONMENT=pokerserver

# virtualenvwrapper.sh has unbound variables. Thus set -eux would break this script.
set -ex

. $(which virtualenvwrapper.sh)

mkvirtualenv --python=$(which python3.6) "${VIRTUAL_ENVIRONMENT}" || true

workon "${VIRTUAL_ENVIRONMENT}"
pip install -r requirements.txt
deactivate
