#!/bin/bash

# Orcutt Chatbot Deployment Script

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

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

# Get AWS region and account from environment or AWS CLI config
AWS_REGION=${AWS_REGION:-$(aws configure get region)}
AWS_ACCOUNT=${AWS_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}

# Set stack name - use environment variable or get from config
STACK_NAME=${STACK_NAME:-$(python3 scripts/get_stack_name.py)}

echo "Deploying Orcutt Chatbot to $ENVIRONMENT environment..."
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo "Stack Name: $STACK_NAME"

# Check if CDK is bootstrapped, if not, bootstrap it
echo "Checking CDK bootstrap status..."
if ! aws ssm get-parameter --name "/cdk-bootstrap/hnb659fds/version" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "CDK not bootstrapped. Running bootstrap..."
    cdk bootstrap "aws://$AWS_ACCOUNT/$AWS_REGION"
else
    echo "CDK already bootstrapped."
fi

# Build frontend first with placeholder API URL
echo "Building frontend with placeholder API URL..."
cd frontend
npm install
REACT_APP_API_BASE_URL="https://placeholder.execute-api.$AWS_REGION.amazonaws.com" npm run build
cd ..

# Deploy CDK stack first and save outputs to file
echo "Deploying CDK stack..."
cdk deploy --require-approval never --outputs-file /tmp/cdk-outputs.json

# Get API URL from outputs file
echo "Getting API URL..."
if [ -f /tmp/cdk-outputs.json ]; then
    API_URL=$(cat /tmp/cdk-outputs.json | grep -o '"https://[^"]*execute-api[^"]*"' | head -1 | tr -d '"')
else
    # Fallback: use CloudFormation API
    API_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)
fi
echo "API URL: $API_URL"

# Rebuild frontend with the real API URL
echo "Rebuilding frontend with real API URL..."
cd frontend
REACT_APP_API_BASE_URL=$API_URL npm run build
cd ..

# Deploy again to update frontend with correct API URL
echo "Deploying frontend with correct API URL..."
cdk deploy --require-approval never

echo "Deployment complete!"
echo "Check AWS Console for deployed resources"
