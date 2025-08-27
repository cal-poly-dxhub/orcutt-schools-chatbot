#!/bin/bash

# Change to project root directory
cd "$(dirname "$0")/.." 

echo "Orcutt Schools - Auto Setup & Webscraper"
echo "============================================"

# Step 1: Get stack name - use environment variable or get from config
echo "Getting stack name..."
STACK_NAME=${STACK_NAME:-$(python3 scripts/get_stack_name.py)}

if [ -z "$STACK_NAME" ]; then
    echo "Could not determine stack name"
    echo "Set STACK_NAME environment variable or check config.yaml"
    exit 1
fi

echo "Using stack: $STACK_NAME"

# Step 2: Extract CDK outputs and setup environment
echo "Step 2: Extracting CDK outputs..."
python3 scripts/setup_env.py "$STACK_NAME"

if [ $? -ne 0 ]; then
    echo "Failed to extract CDK outputs"
    exit 1
fi

# Step 3: Source the environment variables
echo "Step 3: Loading environment variables..."
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "Environment variables loaded"
else
    echo ".env file not found"
    exit 1
fi

# Step 4: Run the webscraper
echo "Step 4: Starting webscraper..."
python3 scripts/invoke_webscraper.py

echo "All done!"