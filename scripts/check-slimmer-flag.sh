#!/bin/bash
# Check if tool-slimmer patch is missing and notify
# Called by Hermes cron every 5 minutes
# If /tmp/.slimmer-patch-missing exists, output the message and delete the flag

FLAG="/tmp/.slimmer-patch-missing"

if [ -f "$FLAG" ]; then
    cat "$FLAG"
    rm -f "$FLAG"
    # Exit 0 = message delivered
    exit 0
else
    # No output = silent, nothing to report
    exit 0
fi
