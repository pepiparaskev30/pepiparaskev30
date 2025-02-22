#!/bin/bash

# Define the file containing the deployment YAML
DEPLOYMENT_FILE="agent_deployment.yaml"

# New node label value (pass as argument or set here)
NEW_NODE_LABEL="$1"

# Check if a new node label value is provided
if [ -z "$NEW_NODE_LABEL" ]; then
  echo "Usage: $0 <new-node-label>"
  exit 1
fi

# Use sed to replace the node label in the YAML file
sed -i "s/\(values:\s*\[\s*\)\"[^"]*\"/\1\"$NEW_NODE_LABEL\"/" "$DEPLOYMENT_FILE"

# Confirm changes
echo "Updated node affinity value in $DEPLOYMENT_FILE to: $NEW_NODE_LABEL"
