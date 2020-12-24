#!/bin/bash

source /amaroq/hass/miniconda3/etc/profile.d/conda.sh
conda activate hass
hass --config /amaroq/hass/config --log-rotate-days 1

