import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import os

def create_opensearch_index(domain_endpoint=None, index_name="orcuttindex", region="us-west-2"):
    # Use provided endpoint or get it automatically
    if not domain_endpoint:
        domain_endpoint = get_domain_endpoint()
        if not domain_endpoint:
            print("Could not get domain endpoint")
            return False
    
    print(f"Creating index '{index_name}' on domain '{domain_endpoint}'")
    
    try:
        # Set up OpenSearch client with AWS auth
        service = "es"  # For managed clusters, use "es" not "aoss"
        credentials = boto3.Session().get_credentials()
        awsauth = AWSV4SignerAuth(credentials, region, service)
        
        os_client = OpenSearch(
            hosts=[{"host": domain_endpoint, "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            timeout=300,
            connection_class=RequestsHttpConnection,
        )
        
        # Simplified index mapping that should work
        mapping = {
            "settings": {
                "index.knn": True
            },
            "mappings": {
                "dynamic": True,
                "properties": {
                    "embeddings": {
                        "type": "knn_vector",
                        "dimension": 1024,  # Titan Text Embedding v2 dimensions
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "faiss",  # Required for Bedrock
                            "parameters": {}
                        }
                    },
                    "AMAZON_BEDROCK_TEXT_CHUNK": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "AMAZON_BEDROCK_METADATA": {
                        "type": "text",
                        "index": True
                    }
                }
            }
        }
        
        # Check if index exists, create if not
        if not os_client.indices.exists(index=index_name):
            print(f"Index '{index_name}' does not exist. Creating...")
            response = os_client.indices.create(index=index_name, body=mapping)
            print(f"Create response: {response}")
            
            # Verify creation
            if os_client.indices.exists(index=index_name):
                print(f"Index '{index_name}' created successfully.")
                return True
            else:
                print(f"Failed to create index '{index_name}'")
                return False
        else:
            print(f"Index '{index_name}' already exists!")
            
            # Optionally, get index info
            try:
                index_info = os_client.indices.get(index=index_name)
                print(f"Index mapping: {json.dumps(index_info[index_name]['mappings'], indent=2, default=str)}")
            except Exception as e:
                print(f"Could not get index info: {e}")
            return True
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def get_domain_endpoint():
    """Helper function to get your OpenSearch domain endpoint"""
    try:
        domain_name = os.environ.get('DOMAIN_NAME', '')
        region = os.environ.get('REGION', 'us-west-2')
        
        opensearch_client = boto3.client('opensearch', region_name=region)
        response = opensearch_client.describe_domain(DomainName=domain_name)
        endpoint = response['DomainStatus']['Endpoint']
        print(f"Found domain endpoint: {endpoint}")
        return endpoint
    except Exception as e:
        print(f"Error getting domain endpoint: {e}")
        return None

def lambda_handler(event, context):
    """Lambda handler for CDK Custom Resource"""
    print("Starting OpenSearch Index Creation Lambda")
    print(f"Event: {json.dumps(event, default=str)}")
    
    if event['RequestType'] == 'Delete':
        print("Delete event - skipping index deletion for safety")
        return {
            'Status': 'SUCCESS', 
            'PhysicalResourceId': 'vector-index',
            'Data': {'Message': 'Index deletion skipped for safety'}
        }
    
    try:
        # Get parameters from CDK
        domain_name = event['ResourceProperties']['DomainName']
        region = event['ResourceProperties']['Region']
        index_name = event['ResourceProperties']['IndexName']
        
        print(f"Starting OpenSearch Index Creation Script")
        print(f"Domain: {domain_name}, Region: {region}, Index: {index_name}")
        
        # Set environment variables for get_domain_endpoint
        os.environ['DOMAIN_NAME'] = domain_name
        os.environ['REGION'] = region
        
        # Create the index
        success = create_opensearch_index(
            domain_endpoint=None,  # Will auto-detect
            index_name=index_name,
            region=region
        )
        
        if success:
            print("Script completed successfully!")
            return {
                'Status': 'SUCCESS',
                'PhysicalResourceId': f'vector-index-{index_name}',
                'Data': {
                    'IndexName': index_name,
                    'Message': f'Index {index_name} created successfully'
                }
            }
        else:
            print("Script failed!")
            return {
                'Status': 'FAILED',
                'Reason': 'Index creation failed'
            }
            
    except Exception as e:
        print(f"Lambda Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'Status': 'FAILED',
            'Reason': f"Lambda failed: {str(e)}"
        }