#!/bin/bash

export WEBSCRAPER_LAMBDA_ARN="arn:aws:lambda:us-west-2:780604190632:function:OrcuttChatbotStack4-dev-WebScraperLambdaCFDBA852-OwWNfMHVjxIW"
export S3_BUCKET_NAME="orcutt-chatbot-kb-4-dev-780604190632-us-west-2"
export KNOWLEDGE_BASE_ID="3THVPBCPJP"
export DATA_SOURCE_ID="0HNO4JYOKI"

echo "Running webscraper with the following configuration:"
echo "Lambda ARN: $WEBSCRAPER_LAMBDA_ARN"
echo "S3 Bucket: $S3_BUCKET_NAME"
echo "Knowledge Base ID: $KNOWLEDGE_BASE_ID"
echo "Data Source ID: $DATA_SOURCE_ID"
echo ""

python3 invoke_webscraper.py