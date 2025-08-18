# infrastructure/orcutt_chatbot_stack.py
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_s3 as s3,
    aws_opensearchservice as opensearch,
    aws_iam as iam,
    aws_ec2 as ec2,
    RemovalPolicy,
)
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    opensearchmanagedcluster,
)


class OrcuttChatbotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for knowledge base documents
        knowledge_base_bucket = s3.Bucket(
            self, "KnowledgeBaseBucket",
            bucket_name=f"orcutt-chatbot-kb-v4-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # OpenSearch Domain for Knowledge Base
        domain = opensearch.Domain(
            self, "KnowledgeBaseOpenSearch",
            domain_name=f"orcutt-kb-v4-{self.account}",
            version=opensearch.EngineVersion.OPENSEARCH_2_3,
            capacity=opensearch.CapacityConfig(
                data_node_instance_type="t3.small.search",
                data_nodes=1
            ),
            ebs=opensearch.EbsOptions(
                volume_size=10,
                volume_type=ec2.EbsDeviceVolumeType.GP3
            ),
            node_to_node_encryption=True,
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            enforce_https=True,
            removal_policy=RemovalPolicy.DESTROY,
            use_unsigned_basic_auth=True,
            access_policies=[
                iam.PolicyStatement(
                    principals=[iam.ServicePrincipal("bedrock.amazonaws.com")],
                    actions=["es:*"],
                    resources=["*"]
                )
            ]
        )

        # OpenSearch Vector Store for Knowledge Base
        opensearch_vector_store = opensearchmanagedcluster.OpenSearchManagedClusterVectorStore(
            domain_arn=domain.domain_arn,
            domain_endpoint=f"https://{domain.domain_endpoint}",
            vector_index_name="orcutt-vector-index",
            field_mapping={
                'metadata_field': 'metadata',
                'text_field': 'text',
                'vector_field': 'vector'
            }
        )

        # Bedrock Knowledge Base using high-level construct
        kb = bedrock.VectorKnowledgeBase(
            self, 'OrcuttKnowledgeBase',
            vector_store=opensearch_vector_store,
            embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_512,
            instruction='Use this knowledge base to answer questions about Orcutt Schools.'
        )

        # S3 Data Source for Knowledge Base
        bedrock.S3DataSource(
            self, 'OrcuttDataSource',
            bucket=knowledge_base_bucket,
            knowledge_base=kb,
            data_source_name='orcutt-school-docs',
            chunking_strategy=bedrock.ChunkingStrategy.SEMANTIC,
            inclusion_prefixes=['documents/']
        )

        # Outputs
        CfnOutput(
            self, "S3BucketName",
            value=knowledge_base_bucket.bucket_name,
            description="S3 bucket for knowledge base"
        )

        CfnOutput(
            self, "OpenSearchDomainEndpoint",
            value=domain.domain_endpoint,
            description="OpenSearch domain endpoint"
        )

        CfnOutput(
            self, "KnowledgeBaseId",
            value=kb.knowledge_base_id,
            description="Bedrock Knowledge Base ID"
        )
