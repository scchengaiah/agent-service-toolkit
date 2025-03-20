from langchain_aws.chat_models.bedrock import ChatBedrock
from langchain_openai import AzureChatOpenAI

from core import settings


def get_azure_openai_model(model_name: str, model_kwargs: dict) -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        deployment_name=model_name,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        **model_kwargs,
    )


def get_bedrock_chat_model(
    model_name: str,
    max_tokens: int = 4096,
    region_name: str = "us-east-1",
    model_kwargs: dict = {},
) -> ChatBedrock:
    return ChatBedrock(
        model=model_name,
        streaming=True,
        max_tokens=max_tokens,
        region_name=region_name,
        model_kwargs=model_kwargs,
    )
