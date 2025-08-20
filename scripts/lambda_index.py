import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def create_opensearch_index(domain_endpoint=None):
    # Configuration
    index_name = "oorcutt-vector-index"
    region = "us-west-2"
    
    # Use provided endpoint or get it automatically
    if not domain_endpoint:
        domain_endpoint = get_domain_endpoint()
        if not domain_endpoint:
            print("❌ Could not get domain endpoint")
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
                    "vector": {
                        "type": "knn_vector",
                        "dimension": 1024,  # Titan Text Embedding v2 dimensions
                        "method": {
                            "name": "hnsw",
                            "space_type": "innerproduct",
                            "engine": "FAISS",  # Required for Bedrock
                            "parameters": {}
                        }
                    },
                    "text": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": False
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
                print(f"✅ Index '{index_name}' created successfully.")
                return True
            else:
                print(f"❌ Failed to create index '{index_name}'")
                return False
        else:
            print(f"ℹ️  Index '{index_name}' already exists!")
            
            # Optionally, get index info
            try:
                index_info = os_client.indices.get(index=index_name)
                print(f"Index mapping: {json.dumps(index_info[index_name]['mappings'], indent=2, default=str)}")
            except Exception as e:
                print(f"Could not get index info: {e}")
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def get_domain_endpoint():
    """Helper function to get your OpenSearch domain endpoint"""
    try:
        opensearch_client = boto3.client('opensearch', region_name='us-west-2')
        response = opensearch_client.describe_domain(DomainName='orcutt-kb-v10-412072465402')
        endpoint = response['DomainStatus']['Endpoint']
        print(f"Found domain endpoint: {endpoint}")
        return endpoint
    except Exception as e:
        print(f"Error getting domain endpoint: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Starting OpenSearch Index Creation Script")
    
    # First, try to get the domain endpoint automatically
    auto_endpoint = get_domain_endpoint()
    if auto_endpoint:
        print(f"Using auto-detected endpoint: {auto_endpoint}")
    
    # Create the index
    success = create_opensearch_index(auto_endpoint)
    
    if success:
        print("🎉 Script completed successfully!")
    else:
        print("💥 Script failed!")
        exit(1)