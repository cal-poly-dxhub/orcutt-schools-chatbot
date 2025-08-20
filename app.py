#!/usr/bin/env python3
from aws_cdk import App
from infrastructure.orcutt_chatbot_stack import OrcuttChatbotStack
from config import get_config

config = get_config()
app = App()

OrcuttChatbotStack(app, config.get_stack_name(),
    env={
        "account": config.AWS_ACCOUNT,
        "region": config.AWS_REGION
    }
)

app.synth()
