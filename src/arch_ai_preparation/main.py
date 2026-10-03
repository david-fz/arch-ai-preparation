import os
import sys
from collections.abc import Callable

from openai import (
    APIConnectionError,
    AuthenticationError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
)

DEFAULT_SCOPE = "https://ai.azure.com/.default"


def resolve_api_key() -> str | Callable[[], str]:
    if os.environ.get("LLM_AUTH", "key") == "entra":
        # Import perezoso: solo se necesita azure-identity con Entra ID.
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        scope = os.environ.get("LLM_TOKEN_SCOPE", DEFAULT_SCOPE)
        return get_bearer_token_provider(DefaultAzureCredential(), scope)
    return os.environ["LLM_API_KEY"]


def missing_env() -> list[str]:
    required = ["LLM_BASE_URL", "LLM_MODEL"]
    if os.environ.get("LLM_AUTH", "key") != "entra":
        required.append("LLM_API_KEY")
    return [name for name in required if not os.environ.get(name)]


def main() -> int:
    if missing := missing_env():
        print(f"Faltan variables de entorno: {', '.join(missing)}", file=sys.stderr)
        return 2

    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=resolve_api_key(),
        timeout=30.0,
        max_retries=1,
    )
    try:
        response = client.chat.completions.create(
            model=os.environ["LLM_MODEL"],
            messages=[{"role": "user", "content": "Responde solo: OK"}],
        )
    except (AuthenticationError, PermissionDeniedError) as e:
        print(f"Credenciales rechazadas (key/rol/scope): {e}", file=sys.stderr)
        return 1
    except NotFoundError as e:
        print(f"404: revisa LLM_BASE_URL y LLM_MODEL ({e})", file=sys.stderr)
        return 1
    except APIConnectionError as e:
        print(f"Sin conexión con {os.environ['LLM_BASE_URL']}: {e}", file=sys.stderr)
        return 1

    content = response.choices[0].message.content
    print(f"Conexión OK · modelo={response.model} · respuesta={content!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
