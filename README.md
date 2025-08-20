  # Orcutt Schools Chatbot

## Table of Contents

- [Collaboration](#collaboration)
- [Disclaimers](#disclaimers)
- [Overview](#overview)
- [Architecture](#architecture)
- [Support](#support)

# Collaboration

Thanks for your interest in our solution. Having specific examples of replication and usage allows us to continue to grow and scale our work. If you clone or use this repository, kindly shoot us a quick email to let us know you are interested in this work!

<wwps-cic@amazon.com>

# Disclaimers

**Customers are responsible for making their own independent assessment of the information in this document.**

**This document:**

(a) is for informational purposes only,

(b) represents current AWS product offerings and practices, which are subject to change without notice, and

(c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions of any kind, whether express or implied. The responsibilities and liabilities of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers.

(d) is not to be considered a recommendation or viewpoint of AWS

**Additionally, all prototype code and associated assets should be considered:**

(a) as-is and without warranties

(b) not suitable for production environments

(d) to include shortcuts in order to support rapid prototyping such as, but not limitted to, relaxed authentication and authorization and a lack of strict adherence to security best practices

**All work produced is open source. More information can be found in the GitHub repo.**

## Authors

- Shrey Shah - <sshah84@calpoly.edu>

## Overview

An AI-powered chatbot built for Orcutt Schools to help students, parents, and staff get information about school programs, schedules, and policies.

## Architecture

The solution consists of several key components:

1. Frontend Interface

    - React 18 application
    - AWS Amplify hosting with global CDN
    - Tailwind CSS for responsive design

2. API Layer

    - Amazon API Gateway for REST endpoints
    - AWS Lambda functions for serverless compute
    - Cognito for Authentication and authorization middleware

3. AI Services

    - Amazon Bedrock with Claude 3.5 Sonnet for response generation
    - AWS Knowledge Bases for semantic document search
    - Nova Lite for query classification and intent recognition
    - Bedrock Guardrails for content safety and filtering

4. Data Storage and Management

    - Amazon DynamoDB for conversation history and user sessions
    - S3 buckets for document storage and knowledge base artifacts
    - Amazon CloudWatch for application monitoring and logging

Additionally other AWS services are used for additional functionality

## Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js 18+ (for frontend)
- Python 3.13+ (for CDK and Lambda functions)
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Request model access for the required models through AWS console in Bedrock (Amazon Titan Text V2 & Claude Sonnet 3.5 V2)
- Docker Desktop

## Deployment Steps

1. Clone the repository
   git clone https://github.com/cal-poly-dxhub/orcutt-schools-chatbot

2. Run the setup script
  ./scripts/setup.sh

3. Start Docker

Ensure Docker Desktop is running on your machine
Verify Docker is running:

bashdocker --version

4. Configure AWS credentials
   aws configure
You'll be prompted to enter:

AWS Access Key ID
AWS Secret Access Key
Default region name
Default output format


5. Deploy the application
./scripts/deploy.sh


Post-Deployment Manual Steps
After deployment is complete, perform these 2 manual tasks:

Run sync in knowledge base
Add the ApiUrl to frontend configuration

Navigate to frontend/services/apiService.js line 5
Update the API URL with your deployed endpoint


## Support

For any queries or issues, please contact:

- Darren Kraker - <dkraker@amazon.com>
- Shrey Shah, Jr. SDE - <sshah84@calpoly.edu>
