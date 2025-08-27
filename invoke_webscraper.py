#!/usr/bin/env python3
"""
Standalone script to invoke the webscraper Lambda function and sync knowledge base.
This script reads the Lambda ARN and other values from environment variables.
"""

import json
import boto3
import os
import sys
import time
from typing import List

def get_env_var(name: str) -> str:
    """Get environment variable or exit if not found."""
    value = os.environ.get(name)
    if not value:
        print(f"Error: Environment variable {name} is required")
        sys.exit(1)
    return value

def invoke_webscraper(lambda_arn: str, s3_bucket: str, websites: List[str]) -> bool:
    """Invoke webscraper Lambda synchronously for each website (like original trigger)."""
    # Increase timeout to handle longer scraping jobs
    config = boto3.session.Config(read_timeout=900)  # 15 minutes
    lambda_client = boto3.client('lambda', config=config)
    success_count = 0
    
    print(f"Starting to scrape {len(websites)} school websites...")
    
    for i, base_url in enumerate(websites, 1):
        print(f"Scraping {i}/{len(websites)}: {base_url}")
        
        try:
            response = lambda_client.invoke(
                FunctionName=lambda_arn,
                InvocationType='RequestResponse',  # Synchronous like original
                Payload=json.dumps({
                    'base_url': base_url,
                    's3_bucket': s3_bucket,
                    'max_workers': 20,
                    'max_pages': 200
                })
            )
            
            # Parse response
            payload = json.loads(response['Payload'].read())
            
            if payload.get('statusCode') == 200:
                print(f"Successfully scraped: {base_url}")
                success_count += 1
            else:
                print(f"Warning: {base_url} failed: {payload}")
                # Continue with other sites instead of failing completely
                
        except Exception as e:
            print(f"Error scraping {base_url}: {str(e)}")
    
    print(f"Scraping completed: {success_count}/{len(websites)} websites successful")
    return success_count > 0

def sync_knowledge_base(kb_id: str, data_source_id: str) -> str:
    """Start knowledge base ingestion job with enhanced error handling."""
    bedrock_agent = boto3.client('bedrock-agent')
    
    try:
        print(f"Starting knowledge base sync for KB: {kb_id}")
        print(f"Data Source ID: {data_source_id}")
        
        # Check if there's already a running ingestion job
        try:
            list_response = bedrock_agent.list_ingestion_jobs(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id,
                maxResults=1
            )
            
            if list_response.get('ingestionJobSummaries'):
                latest_job = list_response['ingestionJobSummaries'][0]
                if latest_job['status'] in ['STARTING', 'IN_PROGRESS']:
                    print(f"Found running ingestion job: {latest_job['ingestionJobId']}")
                    print(f"Status: {latest_job['status']}")
                    return latest_job['ingestionJobId']
        except Exception as list_error:
            print(f"Could not check existing jobs: {str(list_error)}")
        
        # Start new ingestion job
        sync_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        job_id = sync_response['ingestionJob']['ingestionJobId']
        status = sync_response['ingestionJob']['status']
        
        print(f"Knowledge base sync started successfully!")
        print(f"Job ID: {job_id}")
        print(f"Initial Status: {status}")
        
        return job_id
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error starting knowledge base sync: {error_msg}")
        
        # Provide specific error guidance
        if "ValidationException" in error_msg:
            print("Tip: Check that the Knowledge Base and Data Source IDs are correct")
        elif "AccessDeniedException" in error_msg:
            print("Tip: Check that your AWS credentials have bedrock:StartIngestionJob permissions")
        elif "ResourceNotFoundException" in error_msg:
            print("Tip: Verify that the Knowledge Base and Data Source exist and are in the correct region")
        
        return ""

def monitor_ingestion_job(kb_id: str, job_id: str, wait_for_completion: bool = False) -> bool:
    """Monitor ingestion job status and optionally wait for completion."""
    bedrock_agent = boto3.client('bedrock-agent')
    
    try:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=os.environ.get('DATA_SOURCE_ID'),
            ingestionJobId=job_id
        )
        
        job = response['ingestionJob']
        status = job['status']
        
        print(f"Current Status: {status}")
        
        if 'statistics' in job:
            stats = job['statistics']
            if 'numberOfDocumentsScanned' in stats:
                print(f"Documents Scanned: {stats['numberOfDocumentsScanned']}")
            if 'numberOfNewDocumentsIndexed' in stats:
                print(f"New Documents Indexed: {stats['numberOfNewDocumentsIndexed']}")
            if 'numberOfModifiedDocumentsIndexed' in stats:
                print(f"Modified Documents Indexed: {stats['numberOfModifiedDocumentsIndexed']}")
        
        if wait_for_completion and status in ['STARTING', 'IN_PROGRESS']:
            print("Waiting for ingestion to complete...")
            time.sleep(30)
            return monitor_ingestion_job(kb_id, job_id, wait_for_completion)
        
        return status == 'COMPLETE'
        
    except Exception as e:
        print(f"Error monitoring ingestion job: {str(e)}")
        return False

def main():
    """Main function to run webscraper and sync knowledge base."""
    print("Orcutt Schools Webscraper & Knowledge Base Sync")
    print("=" * 50)
    
    # Get required environment variables
    webscraper_arn = get_env_var('WEBSCRAPER_LAMBDA_ARN')
    s3_bucket = get_env_var('S3_BUCKET_NAME')
    kb_id = get_env_var('KNOWLEDGE_BASE_ID')
    data_source_id = get_env_var('DATA_SOURCE_ID')
    
    print(f"Configuration:")
    print(f"  Lambda ARN: {webscraper_arn}")
    print(f"  S3 Bucket: {s3_bucket}")
    print(f"  Knowledge Base: {kb_id}")
    print(f"  Data Source: {data_source_id}")
    print()
    
    # List of all school websites to scrape
    websites = [
        'https://orcuttschools.net',
        'https://orcuttacademy.orcuttschools.net',
        'https://oahs.orcuttschools.net',
        'https://lakeview.orcuttschools.net',
        'https://ojhs.orcuttschools.net',
        'https://aliceshaw.orcuttschools.net',
        'https://joenightingale.orcuttschools.net',
        'https://olgareed.orcuttschools.net',
        'https://pattersonroad.orcuttschools.net',
        'https://pinegrove.orcuttschools.net',
        'https://ralphdunlap.orcuttschools.net',
        'https://osis.orcuttschools.net'
    ]
    
    # Step 1: Invoke webscraper for all websites (synchronous like original)
    scraping_success = invoke_webscraper(webscraper_arn, s3_bucket, websites)
    
    if not scraping_success:
        print("No websites were successfully scraped. Skipping knowledge base sync.")
        sys.exit(1)
    
    print("All websites scraping completed")
    
    # Step 2: Sync knowledge base
    print("\n" + "="*50)
    print("STARTING KNOWLEDGE BASE SYNC")
    print("="*50)
    
    job_id = sync_knowledge_base(kb_id, data_source_id)
    
    if job_id:
        print(f"\nProcess completed successfully!")
        print(f"Ingestion Job ID: {job_id}")
        
        # Check initial status
        print("\nChecking ingestion status...")
        monitor_ingestion_job(kb_id, job_id, wait_for_completion=False)
        
        print(f"\nMonitor progress: AWS Bedrock Console > Knowledge Bases > {kb_id} > Data Sources")
        print(f"Ingestion typically takes 2-5 minutes depending on content size")
        print(f"To check status later, run: aws bedrock-agent get-ingestion-job --knowledge-base-id {kb_id} --data-source-id {data_source_id} --ingestion-job-id {job_id}")
    else:
        print("\nWebscraping completed but knowledge base sync failed.")
        print("Check the error messages above for troubleshooting guidance")
        sys.exit(1)

if __name__ == "__main__":
    main()