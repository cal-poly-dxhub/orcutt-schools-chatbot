"""
Configuration settings for Orcutt Chatbot CDK deployment
"""
import os
import yaml
from pathlib import Path

class Config:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        config_path = Path(__file__).parent / "config.yaml"
        
        with open(config_path, 'r') as file:
            config_data = yaml.safe_load(file)
        
        # AWS Configuration
        aws_config = config_data.get('aws', {})
        self.AWS_REGION = os.environ.get("CDK_DEFAULT_REGION", aws_config.get('region', 'us-west-2'))
        self.AWS_ACCOUNT = os.environ.get("CDK_DEFAULT_ACCOUNT", aws_config.get('account'))
        
        # Stack Configuration
        stack_config = config_data.get('stack', {})
        self.STACK_NAME = stack_config.get('name', 'OrcuttChatbotStack')
        
        # S3 Configuration
        s3_config = config_data.get('s3', {})
        self.S3_KB_BUCKET = s3_config.get('knowledge_base_bucket', 'orcutt-chatbot-kb')
        self.S3_FRONTEND_BUCKET = s3_config.get('frontend_bucket', 'orcutt-chatbot-frontend')
        
        # DynamoDB Configuration
        dynamodb_config = config_data.get('dynamodb', {})
        self.DYNAMODB_TABLE_NAME = dynamodb_config.get('table_name', 'orcutt-conversations')
        
        # Bedrock Configuration
        bedrock_config = config_data.get('bedrock', {})
        self.KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", bedrock_config.get('knowledge_base_id'))
        self.KNOWLEDGE_BASE_NAME = bedrock_config.get('knowledge_base_name', 'OrcuttSchoolsKB')
        self.EMBEDDING_MODEL = bedrock_config.get('embedding_model', 'amazon.titan-embed-text-v2:0')
        
        # Chunking Configuration
        chunking_config = bedrock_config.get('chunking', {})
        self.CHUNKING_STRATEGY = chunking_config.get('strategy', 'SEMANTIC')
        self.CHUNKING_MAX_TOKENS = chunking_config.get('max_tokens', 300)
        self.CHUNKING_BUFFER_SIZE = chunking_config.get('buffer_size', 0)
        self.CHUNKING_BREAKPOINT_THRESHOLD = chunking_config.get('breakpoint_percentile_threshold', 95)
        
        # OpenSearch Configuration
        opensearch_config = config_data.get('opensearch', {})
        self.OPENSEARCH_DOMAIN_NAME = opensearch_config.get('domain_name', 'orcutt-kb')
        self.OPENSEARCH_VERSION = opensearch_config.get('version', '2.3')
        self.OPENSEARCH_INSTANCE_TYPE = opensearch_config.get('instance_type', 't3.small.search')
        self.OPENSEARCH_INSTANCE_COUNT = opensearch_config.get('instance_count', 1)
        self.OPENSEARCH_VOLUME_SIZE = opensearch_config.get('volume_size', 10)
        self.OPENSEARCH_VOLUME_TYPE = opensearch_config.get('volume_type', 'gp3')
        self.OPENSEARCH_INDEX_NAME = opensearch_config.get('index_name', 'orcuttindex')
        self.OPENSEARCH_VECTOR_FIELD = opensearch_config.get('vector_field', 'vector')
        self.OPENSEARCH_TEXT_FIELD = opensearch_config.get('text_field', 'text')
        self.OPENSEARCH_METADATA_FIELD = opensearch_config.get('metadata_field', 'metadata')
        self.OPENSEARCH_VECTOR_DIMENSION = opensearch_config.get('vector_dimension', 1024)
        self.OPENSEARCH_SPACE_TYPE = opensearch_config.get('space_type', 'l2')
        self.OPENSEARCH_ENGINE = opensearch_config.get('engine', 'FAISS')
        
        # Lambda Configuration
        lambda_config = config_data.get('lambda', {})
        self.LAMBDA_TIMEOUT = lambda_config.get('timeout', 300)
        self.LAMBDA_MEMORY = lambda_config.get('memory', 512)
        self.LAMBDA_RUNTIME = lambda_config.get('runtime', 'python3.13')
        
        # Lambda-specific configurations
        webscraper_config = lambda_config.get('webscraper', {})
        self.WEBSCRAPER_TIMEOUT = webscraper_config.get('timeout', 900)
        self.WEBSCRAPER_MEMORY = webscraper_config.get('memory', 1024)
        
        chatbot_config = lambda_config.get('chatbot', {})
        self.CHATBOT_TIMEOUT = chatbot_config.get('timeout', 300)
        self.CHATBOT_MEMORY = chatbot_config.get('memory', 1024)
        
        # API Gateway Configuration
        api_config = config_data.get('api', {})
        self.API_NAME = api_config.get('name', 'OrcuttChatbotAPI')
        cors_config = api_config.get('cors', {})
        self.API_CORS_ALLOW_ORIGINS = cors_config.get('allow_origins', ['*'])
        self.API_CORS_ALLOW_METHODS = cors_config.get('allow_methods', ['GET', 'POST', 'OPTIONS'])
        self.API_CORS_ALLOW_HEADERS = cors_config.get('allow_headers', ['Content-Type', 'Authorization'])
        
        # CloudFront Configuration
        cloudfront_config = config_data.get('cloudfront', {})
        self.CLOUDFRONT_DEFAULT_ROOT_OBJECT = cloudfront_config.get('default_root_object', 'index.html')
        self.CLOUDFRONT_ERROR_RESPONSES = cloudfront_config.get('error_responses', [])
        
        # Environment-specific overrides
        env = self.get_environment()
        env_config = config_data.get('environments', {}).get(env, {})
        
        if 'cors_origins' in env_config:
            self.API_CORS_ALLOW_ORIGINS = env_config['cors_origins']
        
        # Apply environment suffixes
        env_suffix = env_config.get('s3_suffix', '')
        opensearch_suffix = env_config.get('opensearch_suffix', '')
        
        if env_suffix:
            self.S3_KB_BUCKET = f"{self.S3_KB_BUCKET}-{env_suffix}"
            self.S3_FRONTEND_BUCKET = f"{self.S3_FRONTEND_BUCKET}-{env_suffix}"
        
        if opensearch_suffix:
            self.OPENSEARCH_DOMAIN_NAME = f"{self.OPENSEARCH_DOMAIN_NAME}-{opensearch_suffix}"
    
    def get_environment(self):
        return os.environ.get("ENVIRONMENT", "dev")
    
    def is_production(self):
        return self.get_environment().lower() == "prod"
    
    def get_stack_name(self):
        env = self.get_environment()
        return f"{self.STACK_NAME}-{env}" if env != "prod" else self.STACK_NAME
    
    def get_s3_bucket_name(self, bucket_type='kb'):
        """Get S3 bucket name with account and region suffix"""
        base_name = self.S3_KB_BUCKET if bucket_type == 'kb' else self.S3_FRONTEND_BUCKET
        return f"{base_name}-{self.AWS_ACCOUNT}-{self.AWS_REGION}"
    
    def get_opensearch_domain_name(self):
        """Get OpenSearch domain name with account suffix (max 28 chars)"""
        # Use last 6 digits of account to stay under 28 char limit
        account_suffix = str(self.AWS_ACCOUNT)[-6:] if self.AWS_ACCOUNT else "123456"
        env = self.get_environment()
        base_name = self.OPENSEARCH_DOMAIN_NAME
        if env != "prod":
            return f"{base_name}-{env}-{account_suffix}"[:28]
        return f"{base_name}-{account_suffix}"[:28]
    
    def get_dynamodb_table_name(self):
        """Get DynamoDB table name with account suffix"""
        return f"{self.DYNAMODB_TABLE_NAME}-{self.AWS_ACCOUNT}"

def get_config():
    """Get configuration instance"""
    return Config()