#!/bin/bash

# Orcutt Chatbot Deployment Script

echo "🚀 Starting Orcutt Chatbot deployment..."

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ CDK CLI not found. Please install it first:"
    echo "npm install -g aws-cdk"
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install CDK dependencies
echo "📥 Installing CDK dependencies..."
pip install -r requirements.txt

# Install Lambda dependencies
echo "📥 Installing Lambda dependencies..."
pip install -r lambda/requirements.txt -t lambda/

# Bootstrap CDK (run only once per account/region)
echo "🏗️  Bootstrapping CDK..."
cdk bootstrap

# Synthesize CloudFormation template
echo "🔍 Synthesizing CloudFormation template..."
cdk synth

# Deploy the stack
echo "🚀 Deploying stack..."
cdk deploy --require-approval never

echo "✅ Deployment complete!"
echo "📝 Don't forget to update these environment variables in the Lambda function:"
echo "   - KNOWLEDGE_BASE_ID"
echo "   - GUARDRAIL_ID"
echo "   - GUARDRAIL_VERSION"