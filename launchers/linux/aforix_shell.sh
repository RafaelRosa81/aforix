#!/usr/bin/env bash

# Aforix shell launcher

source activate aforix

cd "$(dirname "$0")/../.."

exec "$SHELL"
