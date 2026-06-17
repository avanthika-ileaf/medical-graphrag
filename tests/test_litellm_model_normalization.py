import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config, normalise_litellm_model
from src.llm.litellm_client import LiteLLMClient


def test_config_normalises_legacy_regolo_prefix() -> None:
    assert normalise_litellm_model("regolo/Llama-3.3-70B-Instruct") == "openai/Llama-3.3-70B-Instruct"


def test_config_get_litellm_model_normalises_explicit_model() -> None:
    assert Config.get_litellm_model(model="regolo/qwen3.5-9b") == "openai/qwen3.5-9b"


def test_litellm_client_normalises_legacy_regolo_prefix() -> None:
    client = LiteLLMClient(model="regolo/Llama-3.3-70B-Instruct")

    assert client.original_model == "openai/Llama-3.3-70B-Instruct"
    assert client.model == "openai/Llama-3.3-70B-Instruct"
    assert client.provider_alias is None


def test_default_litellm_client_uses_regolo_credentials() -> None:
    client = LiteLLMClient()

    assert client.model.startswith("openai/")
    assert client.api_base == Config.LITELLM_API_BASE
    assert client.api_key == Config.REGOLO_API_KEY
