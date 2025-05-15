#!/bin/bash

# Duration for each component
DURATION=300  # 5 minutes

# Run CPU and memory stress in background
stress-ng --cpu 4 --vm 2 --vm-bytes 500M --timeout ${DURATION}s &

# Simulate network load to loopback (causes TX/RX in node_exporter)
while true; do
  curl -s http://127.0.0.1:80 > /dev/null || true
  sleep 0.1
done
