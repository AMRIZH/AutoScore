#!/bin/bash
set -e

# Ensure mounted directories exist and are writable by appuser
for dir in /app/instance /app/logs /app/results /app/uploads; do
    mkdir -p "$dir"
    chown -R appuser:appuser "$dir"
done

# Drop privileges and run command as appuser
exec gosu appuser "$@"
