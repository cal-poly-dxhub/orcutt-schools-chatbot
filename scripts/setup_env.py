#!/usr/bin/env python3
"""
Helper script to extract CDK outputs and set up environment variables for the webscraper.
Run this after CDK deployment to get the required values.
"""

import json
import boto3
import os
import sys

def get_stack_outputs(stack_name: str) -> dict:
    """Get CDK stack outputs."""
    try:
        cloudformation = boto3.client('cloudformation')
        response = cloudformation.describe_stacks(StackName=stack_name)
        
        if not response['Stacks']:
            print(f"Stack {stack_name} not found")
            return {}
        
        stack = response['Stacks'][0]
        outputs = {}
        
        for output in stack.get('Outputs', []):
            outputs[output['OutputKey']] = output['OutputValue']
        
        return outputs
        
    except Exception as e:
        print(f"Error getting stack outputs: {str(e)}")
        return {}

def create_env_file(outputs: dict, filename: str = '.env'):
    """Create or update environment file with the required variables."""
    required_outputs = {
        'WEBSCRAPER_LAMBDA_ARN': 'WebScraperLambdaArn',
        'S3_BUCKET_NAME': 'S3BucketName', 
        'KNOWLEDGE_BASE_ID': 'KnowledgeBaseId',
        'DATA_SOURCE_ID': 'DataSourceId'
    }
    
    # Read existing .env file if it exists
    existing_vars = {}
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_vars[key] = value
    
    env_content = []
    missing_outputs = []
    
    # Update with new values from CDK outputs
    for env_var, output_key in required_outputs.items():
        if output_key in outputs:
            value = outputs[output_key]
            # Fix Data Source ID format (extract second part after |)
            if env_var == 'DATA_SOURCE_ID' and '|' in value:
                value = value.split('|')[1]
            existing_vars[env_var] = value
        else:
            missing_outputs.append(output_key)
    
    if missing_outputs:
        print(f"Missing required outputs: {', '.join(missing_outputs)}")
        return False
    
    # Write all variables back to .env file
    for key, value in existing_vars.items():
        env_content.append(f"{key}={value}")
    
    with open(filename, 'w') as f:
        f.write('\n'.join(env_content))
        f.write('\n')
    
    print(f"Environment file updated: {filename}")
    return True

def create_shell_script(outputs: dict, filename: str = 'run_webscraper.sh'):
    """Create shell script to run webscraper with environment variables."""
    required_outputs = {
        'WEBSCRAPER_LAMBDA_ARN': 'WebScraperLambdaArn',
        'S3_BUCKET_NAME': 'S3BucketName',
        'KNOWLEDGE_BASE_ID': 'KnowledgeBaseId', 
        'DATA_SOURCE_ID': 'DataSourceId'
    }
    
    script_content = ['#!/bin/bash', '']
    
    for env_var, output_key in required_outputs.items():
        if output_key in outputs:
            value = outputs[output_key]
            # Fix Data Source ID format (extract second part after |)
            if env_var == 'DATA_SOURCE_ID' and '|' in value:
                value = value.split('|')[1]
            script_content.append(f'export {env_var}="{value}"')
    
    script_content.extend([
        '',
        'echo "🚀 Running webscraper with the following configuration:"',
        'echo "Lambda ARN: $WEBSCRAPER_LAMBDA_ARN"',
        'echo "S3 Bucket: $S3_BUCKET_NAME"', 
        'echo "Knowledge Base ID: $KNOWLEDGE_BASE_ID"',
        'echo "Data Source ID: $DATA_SOURCE_ID"',
        'echo ""',
        '',
        'python3 invoke_webscraper.py'
    ])
    
    with open(filename, 'w') as f:
        f.write('\n'.join(script_content))
    
    # Make executable
    os.chmod(filename, 0o755)
    
    print(f"Shell script created: {filename}")
    return True

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python3 setup_env.py <stack-name>")
        print("Example: python3 setup_env.py OrcuttChatbotStack")
        sys.exit(1)
    
    stack_name = sys.argv[1]
    
    print(f"Getting outputs from CDK stack: {stack_name}")
    outputs = get_stack_outputs(stack_name)
    
    if not outputs:
        print("No outputs found or error occurred")
        sys.exit(1)
    
    print(f"Found {len(outputs)} outputs:")
    for key, value in outputs.items():
        print(f"  {key}: {value}")
    
    print()
    
    # Create .env file
    if create_env_file(outputs):
        print("You can now run: python3 invoke_webscraper.py")
    
    # Create shell script
    if create_shell_script(outputs):
        print("Or run: ./run_webscraper.sh")

if __name__ == "__main__":
    main()