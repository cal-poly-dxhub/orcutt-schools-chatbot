#!/bin/bash

# Orcutt Chatbot Setup Script

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "Setting up Orcutt Chatbot..."

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is required but not installed."
    exit 1
fi

if ! command -v cdk &> /dev/null; then
    echo "AWS CDK is required. Installing..."
    npm install -g aws-cdk
fi

# Create and activate virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Copy environment template
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "WARNING: Please edit .env file with your AWS account details and Knowledge Base ID"
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. aws configure"
echo "3. Run './scripts/deploy.sh' to deploy the application"
