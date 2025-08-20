#!/bin/bash

# Orcutt Chatbot Deployment Script

set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "Loading environment variables..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default environment if not specified
ENVIRONMENT=${ENVIRONMENT:-dev}

echo "Deploying Orcutt Chatbot to $ENVIRONMENT environment..."

# Build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Deploy CDK stack
echo "Deploying CDK stack..."
cdk deploy --require-approval never

echo "Deployment complete!"
echo "Check AWS Console for deployed resources"