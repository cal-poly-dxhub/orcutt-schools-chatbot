#!/usr/bin/env python3
import boto3
import json
import time

def invoke_webscraper_batches(lambda_arn, base_url, s3_bucket, total_pages=200, batch_size=50):
    """Invoke multiple Lambda functions for large scraping jobs"""
    lambda_client = boto3.client('lambda')
    
    num_batches = (total_pages + batch_size - 1) // batch_size
    results = []
    
    for i in range(num_batches):
        payload = {
            'base_url': base_url,
            's3_bucket': s3_bucket,
            'max_workers': 4,
            'max_pages': batch_size
        }
        
        response = lambda_client.invoke(
            FunctionName=lambda_arn,
            InvocationType='Event',  # Async
            Payload=json.dumps(payload)
        )
        
        results.append({'batch': i+1, 'status': 'invoked', 'statusCode': response['StatusCode']})
        print(f"Batch {i+1}/{num_batches} invoked successfully")
        
        # Small delay between invocations to avoid throttling
        time.sleep(2)
    
    return results

if __name__ == "__main__":
    lambda_arn = "arn:aws:lambda:us-west-2:412072465402:function:OrcuttChatbotStack14-WebScraperLambdaCFDBA852-KRDhMeqqtF8V"
    s3_bucket = "orcutt-chatbot-kb-v17-412072465402-us-west-2"

    # Websites to scrape
    sites = [
        "https://www.orcuttschools.net/"
        "https://orcuttacademy.orcuttschools.net/",
        "https://oahs.orcuttschools.net/",
        "https://lakeview.orcuttschools.net/",
        "https://ojhs.orcuttschools.net/",
        "https://aliceshaw.orcuttschools.net/",
        "https://joenightingale.orcuttschools.net/",
        "https://olgareed.orcuttschools.net/",
        "https://pattersonroad.orcuttschools.net/",
        "https://pinegrove.orcuttschools.net/",
        "https://ralphdunlap.orcuttschools.net/",
        "https://osis.orcuttschools.net/"
    ]
    
    for site in sites:
        print(f"\n🚀 Starting batch scraping for: {site}")
        print(f"Total pages: 200, Batch size: 50, Number of batches: 4")
        
        results = invoke_webscraper_batches(
            lambda_arn=lambda_arn,
            base_url=site,
            s3_bucket=s3_bucket,
            total_pages=200,
            batch_size=50
        )
        
        print(f"✅ All batches invoked for {site}")
        print(f"Results: {results}")
        print("-" * 80)
    
    print("\n📝 Note: Check CloudWatch logs and S3 bucket for scraping progress")
    print("Log group: /aws/lambda/OrcuttChatbotStack14-WebScraperLambda...")