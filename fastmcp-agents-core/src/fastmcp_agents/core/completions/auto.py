import logging
import os
from functools import cache
from logging import Logger
from typing import NoReturn

from fastmcp_agents.core.completions.base import LLMCompletionsProtocol

logger: Logger = logging.getLogger(name="fastmcp_agents.providers")


def raise_missing_llm() -> NoReturn:
    """Raise an error if the LLM completions are not set."""

    msg = "No LLM completions provider has been set."
    raise ValueError(msg)


def required_llm() -> LLMCompletionsProtocol:
    """Get the required LLM completions."""

    return auto_llm() or raise_missing_llm()


@cache
def auto_llm() -> LLMCompletionsProtocol | None:
    """Convert the completions options to a completions provider."""

    provider = os.getenv("MODEL_PROVIDER")

    selected_llm: LLMCompletionsProtocol | None = None

    if provider == "vertex_ai":
        logger.info("Vertex AI has been selected as the model provider.")

        from google import genai
        from google.genai import Client as GoogleGenaiClient
        from google.oauth2 import service_account

        from fastmcp_agents.core.completions.gemini import GoogleGenaiCompletions

        credentials: service_account.Credentials | None = None

        if credentials_json := os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            scopes = [
                "https://www.googleapis.com/auth/generative-language",
                "https://www.googleapis.com/auth/cloud-platform",
            ]

            credentials = service_account.Credentials.from_service_account_file(filename=credentials_json, scopes=scopes)  # pyright: ignore[reportUnknownMemberType]

        selected_llm = GoogleGenaiCompletions(
            client=GoogleGenaiClient(vertexai=True, credentials=credentials),
            default_model=os.getenv("MODEL") or "gemini-2.5-flash",
        )

    if provider == "gemini":
        logger.info("Gemini has been selected as the model provider.")

        from google import genai
        from google.genai import Client as GoogleGenaiClient

        from fastmcp_agents.core.completions.gemini import GoogleGenaiCompletions

        genai_client: GoogleGenaiClient = genai.Client()

        selected_llm = GoogleGenaiCompletions(
            client=genai_client,
            default_model=os.getenv("MODEL") or "gemini-2.5-flash",
        )

    if provider == "openai":
        logger.info("OpenAI has been selected as the model provider.")

        from openai import OpenAI

        from fastmcp_agents.core.completions.openai import OpenAILLMCompletions

        openai_client: OpenAI = OpenAI(
            api_key=os.getenv("API_KEY"),
        )

        selected_llm = OpenAILLMCompletions(
            default_model=os.getenv("MODEL") or "gpt-4.1-mini",  # pyright: ignore[reportArgumentType]
            client=openai_client,
        )

    if provider == "litellm":
        logger.info("Litellm has been selected as the model provider.")

        from fastmcp_agents.core.completions.litellm import LiteLLMCompletions

        selected_llm = LiteLLMCompletions(
            default_model=os.getenv("MODEL") or "openai/gpt-4.1-mini",
        )

    return selected_llm
