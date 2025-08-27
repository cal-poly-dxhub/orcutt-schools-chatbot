from aws_cdk import (
    Stack,
    CfnOutput,
    aws_s3 as s3,
    aws_opensearchservice as opensearch,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_dynamodb,
    aws_apigateway as apigateway,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3deploy,
    custom_resources as cr,
    RemovalPolicy,
    Duration,
    CustomResource,
    aws_bedrock as bedrock
)
from constructs import Construct
from config import get_config
import json

class OrcuttChatbotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Load configuration
        self.config = get_config()

        # S3 Bucket for knowledge base documents
        knowledge_base_bucket = s3.Bucket(
            self, "KnowledgeBaseBucket",
            bucket_name=self.config.get_s3_bucket_name('kb'),
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY
        )
        source_bucket = s3.Bucket.from_bucket_name(self, "SourceBucket", self.config.get_s3_bucket_name('kb'))

        # OpenSearch Domain for Knowledge Base
        domain = opensearch.Domain(
            self, "KnowledgeBaseOpenSearch",
            domain_name=self.config.get_opensearch_domain_name(),
            version=getattr(opensearch.EngineVersion, f"OPENSEARCH_{str(self.config.OPENSEARCH_VERSION).replace('.', '_')}"),
            capacity=opensearch.CapacityConfig(
                data_node_instance_type=self.config.OPENSEARCH_INSTANCE_TYPE,
                data_nodes=self.config.OPENSEARCH_INSTANCE_COUNT
            ),
            ebs=opensearch.EbsOptions(
                volume_size=self.config.OPENSEARCH_VOLUME_SIZE,
                volume_type=getattr(ec2.EbsDeviceVolumeType, self.config.OPENSEARCH_VOLUME_TYPE.upper())
            ),
            node_to_node_encryption=True,
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            enforce_https=True,
            removal_policy=RemovalPolicy.DESTROY,
            vpc=None
        )

        # IAM Role for Bedrock Knowledge Base
        bedrock_kb_role = iam.Role(
            self, "BedrockKnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                knowledge_base_bucket.bucket_arn,
                                f"{knowledge_base_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                ),
                "BedrockAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel"
                            ],
                            resources=[
                                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"
                            ]
                        )
                    ]
                ),
                "OpenSearchAccess": iam.PolicyDocument(
                    statements=[
                        # OpenSearch domain validation
                        iam.PolicyStatement(
                            sid="OpenSearchManagedClusterDomainValidation",
                            actions=[
                                "es:DescribeDomain"
                            ],
                            resources=[
                                domain.domain_arn
                            ]
                        ),
                        # Index-level access for CRUD operations
                        iam.PolicyStatement(
                            sid="OpenSearchManagedClusterIndexAccess",
                            actions=[
                                "es:ESHttpGet",
                                "es:ESHttpPost", 
                                "es:ESHttpPut",
                                "es:ESHttpDelete"
                            ],
                            resources=[
                                f"{domain.domain_arn}/orcuttindex/*"
                            ]
                        ),
                        # Index metadata access
                        iam.PolicyStatement(
                            sid="OpenSearchManagedClusterGetIndexAccess",
                            actions=[
                                "es:ESHttpGet",
                                "es:ESHttpHead"
                            ],
                            resources=[
                                f"{domain.domain_arn}/orcuttindex"
                            ]
                        )
                    ]
                )
            }
        )

        # Add access policies to domain after bedrock_kb_role is defined
        domain.add_access_policies(
            iam.PolicyStatement(
                principals=[
                    iam.ServicePrincipal("bedrock.amazonaws.com"),
                    bedrock_kb_role,
                    iam.AccountRootPrincipal()
                ],
                actions=["es:*"],
                resources=[f"arn:aws:es:{self.region}:{self.account}:domain/{self.config.get_opensearch_domain_name()}/*"]
            )
        )

        # Lambda Layer for opensearch-py
        opensearch_layer = lambda_.LayerVersion(
            self, "OpenSearchLayer",
            code=lambda_.Code.from_asset("lambda-layers/opensearch-layer", bundling={
                "image": lambda_.Runtime.PYTHON_3_9.bundling_image,
                "command": [
                    "bash", "-c",
                    "pip install -r requirements.txt -t /asset-output/python"
                ]
            }),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="OpenSearch Python client library"
        )

        # Enhanced IAM Role for Index Creator Lambda
        index_creator_role = iam.Role(
            self, "IndexCreatorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "OpenSearchAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "es:*",
                                "es:ESHttpGet",
                                "es:ESHttpPost", 
                                "es:ESHttpPut",
                                "es:ESHttpDelete",
                                "es:ESHttpHead",
                                "es:DescribeDomain",
                                "es:DescribeElasticsearchDomain",
                                "es:ListDomainNames",
                                "es:ListElasticsearchInstanceTypes"
                            ],
                            resources=[
                                domain.domain_arn, 
                                f"{domain.domain_arn}/*",
                                "*" 
                            ]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "opensearch:*"
                            ],
                            resources=[
                                domain.domain_arn,
                                f"{domain.domain_arn}/*",
                                "*"
                            ]
                        )
                    ]
                )
            }
        )

        # Lambda function for creating Vector Index
        index_creator = lambda_.Function(
            self, "IndexCreator",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            role=index_creator_role,
            timeout=Duration.minutes(10),
            layers=[opensearch_layer],
            environment={
                "DOMAIN_NAME": self.config.get_opensearch_domain_name(),
                "REGION": self.region
            },
            code=lambda_.Code.from_asset("scripts")
        )

        # Custom resource to create/check the vector index
        index_creation = CustomResource(
            self, "VectorIndexCreation",
            service_token=cr.Provider(
                self, "IndexCreationProvider",
                on_event_handler=index_creator
            ).service_token,
            properties={
                "DomainName": self.config.get_opensearch_domain_name(),
                "IndexName": self.config.OPENSEARCH_INDEX_NAME,
                "Region": self.region
            }
        )

        # Ensure index is created after domain
        index_creation.node.add_dependency(domain)

        bedrock_role = iam.Role(self, "BedrockKBRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonOpenSearchServiceFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess")
            ]
        )

        # Create the Knowledge Base
        kb = bedrock.CfnKnowledgeBase(self, "KnowledgeBase",
            name=self.config.KNOWLEDGE_BASE_NAME,
            role_arn=bedrock_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/{self.config.EMBEDDING_MODEL}"
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_MANAGED_CLUSTER",
                opensearch_managed_cluster_configuration=bedrock.CfnKnowledgeBase.OpenSearchManagedClusterConfigurationProperty(
                    domain_endpoint=f"https://{domain.domain_endpoint}",
                    domain_arn=domain.domain_arn,
                    vector_index_name=self.config.OPENSEARCH_INDEX_NAME,
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchManagedClusterFieldMappingProperty(
                        vector_field=self.config.OPENSEARCH_VECTOR_FIELD,
                        text_field=self.config.OPENSEARCH_TEXT_FIELD,
                        metadata_field=self.config.OPENSEARCH_METADATA_FIELD
                    )
                )
            )
        )
                
        kb.node.add_dependency(index_creation)

        # Create the data source
        data_source = bedrock.CfnDataSource(
            self,
            "KnowledgeBaseDataSource",
            knowledge_base_id=kb.ref,
            name=source_bucket.bucket_name,
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=source_bucket.bucket_arn
                ),
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy=self.config.CHUNKING_STRATEGY,
                    semantic_chunking_configuration=bedrock.CfnDataSource.SemanticChunkingConfigurationProperty(
                        breakpoint_percentile_threshold=self.config.CHUNKING_BREAKPOINT_THRESHOLD,
                        buffer_size=self.config.CHUNKING_BUFFER_SIZE,
                        max_tokens=self.config.CHUNKING_MAX_TOKENS,
                    ),
                ),
            ),
        )


        # Web Scraper Layer
        webscraper_layer = lambda_.LayerVersion(
            self, "WebScraperLayer",
            code=lambda_.Code.from_asset("lambda-layers/webscraper-layer", bundling={
                "image": lambda_.Runtime.PYTHON_3_13.bundling_image,
                "command": [
                    "bash", "-c",
                    "pip install -r requirements.txt -t /asset-output/python"
                ]
            }),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_13],
            description="Web scraping dependencies"
        )

        # Web Scraper Lambda Function
        webscraper_lambda = lambda_.Function(
            self, "WebScraperLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/webscraper"),
            timeout=Duration.seconds(self.config.WEBSCRAPER_TIMEOUT),
            layers=[webscraper_layer],
            environment={
                "S3_BUCKET_NAME": source_bucket.bucket_name
            },
            memory_size=self.config.WEBSCRAPER_MEMORY
        )

        # Grant S3 permissions to Lambda
        source_bucket.grant_write(webscraper_lambda)
        
        # Grant Bedrock permissions to webscraper for auto-sync
        webscraper_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:StartIngestionJob", "bedrock:GetIngestionJob"],
                resources=[f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/*"]
            )
        )
        


        # DynamoDB table for conversation history
        conversation_table = aws_dynamodb.Table(
            self, "ConversationTable",
            table_name=self.config.get_dynamodb_table_name(),
            partition_key=aws_dynamodb.Attribute(
                name="session_id",
                type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="timestamp",
                type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Chatbot Lambda Function
        chatbot_lambda = lambda_.Function(
            self, "ChatbotLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.X86_64,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/chatbot"),
            timeout=Duration.seconds(self.config.CHATBOT_TIMEOUT),
            memory_size=self.config.CHATBOT_MEMORY,
            environment={
                "DYNAMODB_TABLE": conversation_table.table_name,
                "KNOWLEDGE_BASE_ID": kb.ref
            }
        )

        # Grant permissions to chatbot Lambda
        conversation_table.grant_read_write_data(chatbot_lambda)
        chatbot_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:*"],
                resources=["*"]
            )
        )

        # API Gateway
        api = apigateway.RestApi(
            self, "ChatbotApi",
            rest_api_name=self.config.API_NAME,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=self.config.API_CORS_ALLOW_ORIGINS,
                allow_methods=self.config.API_CORS_ALLOW_METHODS,
                allow_headers=self.config.API_CORS_ALLOW_HEADERS
            )
        )

        # API Gateway resources and methods
        lambda_integration = apigateway.LambdaIntegration(chatbot_lambda)
        
        # /chat resource
        chat_resource = api.root.add_resource("chat")
        chat_resource.add_method("POST", lambda_integration)
        
        # /feedback resource
        feedback_resource = api.root.add_resource("feedback")
        feedback_resource.add_method("POST", lambda_integration)
        
        # /sources resource
        sources_resource = api.root.add_resource("sources")
        
        # /sources/{sourceId} resource
        source_id_resource = sources_resource.add_resource("{sourceId}")
        source_id_resource.add_method("GET", lambda_integration)

        # Frontend S3 bucket
        frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            removal_policy=RemovalPolicy.DESTROY
        )

        # CloudFront distribution
        error_responses = []
        for error_config in self.config.CLOUDFRONT_ERROR_RESPONSES:
            error_responses.append(
                cloudfront.ErrorResponse(
                    http_status=error_config['http_status'],
                    response_http_status=error_config['response_http_status'],
                    response_page_path=error_config['response_page_path']
                )
            )
        
        distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            ),
            default_root_object=self.config.CLOUDFRONT_DEFAULT_ROOT_OBJECT,
            error_responses=error_responses
        )

        # Deploy React build to S3 (build folder must exist)
        s3deploy.BucketDeployment(
            self, "DeployFrontend",
            sources=[s3deploy.Source.asset("frontend/build")],
            destination_bucket=frontend_bucket,
            distribution=distribution,
            distribution_paths=["/*"]
        )

        # Outputs
        CfnOutput(
            self, "WebScraperLambdaArn",
            value=webscraper_lambda.function_arn,
            description="Web scraper Lambda function ARN"
        )

        CfnOutput(
            self, "ChatbotLambdaArn",
            value=chatbot_lambda.function_arn,
            description="Chatbot Lambda function ARN"
        )

        CfnOutput(
            self, "ApiUrl",
            value=api.url,
            description="API Gateway URL"
        )

        CfnOutput(
            self, "WebsiteUrl",
            value=f"https://{distribution.distribution_domain_name}",
            description="CloudFront URL"
        )

        CfnOutput(
            self, "S3BucketName",
            value=source_bucket.bucket_name,
            description="S3 bucket for knowledge base"
        )

        CfnOutput(
            self, "DynamoDBTableName",
            value=conversation_table.table_name,
            description="DynamoDB table for conversations"
        )

        CfnOutput(
            self, "KnowledgeBaseId",
            value=kb.ref,
            description="Bedrock Knowledge Base ID"
        )

        CfnOutput(
            self, "DataSourceId",
            value=data_source.ref,
            description="Bedrock Data Source ID"
        )
