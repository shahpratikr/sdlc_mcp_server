#!/usr/bin/env bash
set -e

curl -sSL https://install.python-poetry.org | python3 - --version 2.4.1

echo -e "\nInstalling poetry venv and activate...\n"
poetry install

echo -e "\nInstalling pre-commit hooks...\n"
poetry run pre-commit install
