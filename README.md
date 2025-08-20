# Orcutt Schools Chatbot

A serverless chatbot application built with AWS CDK, featuring a React frontend and AWS Bedrock-powered backend for school information queries.

## Architecture

- **Frontend**: React application hosted on S3 with CloudFront distribution
- **Backend**: AWS Lambda functions with API Gateway
- **Database**: DynamoDB for conversation history
- **AI**: AWS Bedrock Knowledge Base with Nova models
- **Web Scraping**: Automated Lambda function for content ingestion

## Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js 18+ (for frontend)
- Python 3.13+ (for CDK and Lambda functions)
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Environment Setup

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd orcutt_cdk
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual values:
# - CDK_DEFAULT_ACCOUNT: Your AWS account ID
# - AWS_ACCESS_KEY_ID: Your AWS access key
# - AWS_SECRET_ACCESS_KEY: Your AWS secret key
# - KNOWLEDGE_BASE_ID: Your Bedrock knowledge base ID
```

3. **Install frontend dependencies:**
```bash
cd frontend
npm install
cd ..
```

## Deployment

### Development Environment
```bash
# Deploy to development
export ENVIRONMENT=dev
cdk deploy --require-approval never
```

### Production Environment
```bash
# Deploy to production
export ENVIRONMENT=prod
cdk deploy --require-approval never
```

### Web Scraping Setup
```bash
# Run the web scraper to populate knowledge base
python scripts/invoke_scraper.py

# Create OpenSearch index (if needed)
python scripts/lambda_index.py
```

## Project Structure

```
orcutt_cdk/
├── app.py                 # CDK app entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── infrastructure/        # CDK stack definitions
├── lambda/               # Lambda function code
│   ├── chatbot/         # Main chatbot Lambda
│   └── webscraper/      # Web scraping Lambda
├── frontend/            # React application
├── scripts/             # Utility scripts
└── README.md
```

## Configuration

Edit `config.py` to customize:
- AWS region and account settings
- Lambda timeout and memory settings
- CORS origins for API Gateway
- Environment-specific configurations

## API Endpoints

After deployment, the following endpoints are available:

- `POST /chat` - Send messages to chatbot
- `POST /feedback` - Submit feedback for responses
- `GET /sources` - Retrieve conversation sources

## Frontend

The React frontend provides:
- Real-time chat interface
- Conversation history
- Source citations
- Feedback system

## Monitoring

- CloudWatch logs for all Lambda functions
- DynamoDB metrics for conversation storage
- API Gateway metrics for request monitoring

## Security

- CORS configured for API Gateway
- IAM roles with least privilege access
- Environment-specific configurations
- No hardcoded credentials

## Development

### Local Frontend Development
```bash
cd frontend
npm start
```

### Testing Lambda Functions
```bash
# Test chatbot locally (requires AWS credentials)
python lambda/chatbot/lambda_function.py
```

## Troubleshooting

1. **CDK Deploy Issues**: Ensure AWS credentials are configured
2. **Lambda Timeouts**: Check CloudWatch logs for performance issues
3. **CORS Errors**: Verify API Gateway CORS configuration
4. **Knowledge Base**: Ensure KNOWLEDGE_BASE_ID is set correctly

## Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## License

[Add your license information here]