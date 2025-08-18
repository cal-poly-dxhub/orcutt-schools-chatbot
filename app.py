#!/usr/bin/env python3
import os
from aws_cdk import App
from infrastructure.orcutt_chatbot_stack import OrcuttChatbotStack

app = App()

OrcuttChatbotStack(app, "OrcuttChatbotStackV2",
    env={
        "account": os.environ.get("CDK_DEFAULT_ACCOUNT"),
        "region": os.environ.get("CDK_DEFAULT_REGION", "us-west-2")
    }
)

app.synth()
