#!/bin/bash

echo "Running panel loop"
while true
do
   echo "Starting panel"
   python3 /amaroq/hass/clients/panel.py
   sleep 2
done

