#!/bin/bash

set -eu

# Ensure all subprocess commands terminate.
trap 'kill $(jobs -p)' EXIT

echo "Get up." | festival --tts

