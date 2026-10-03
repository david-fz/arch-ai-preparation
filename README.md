# arch-ai-preparation

Smoke test para validar la conexión con un endpoint compatible con OpenAI (Chat Completions).
Funciona con Microsoft Foundry (Entra ID) y con cualquier proveedor que exponga
`/v1/chat/completions` (Ollama, vLLM, LM Studio, OpenRouter, OpenAI…). Cambiar de proveedor
solo requiere editar variables de entorno; el código no cambia.

## Requisitos

- [uv](https://docs.astral.sh/uv/) y Python 3.14 (ver `.python-version`)
- Perfil Foundry: Azure CLI (`az login`) y rol **Azure AI User** sobre el proyecto
- Perfil Ollama: `ollama serve` y un modelo descargado (`ollama pull llama3.2`)

## Instalación

```bash
uv sync
cp .env.example .env   # deja activo un solo perfil
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `LLM_BASE_URL` | Sí | URL base compatible con OpenAI |
| `LLM_MODEL` | Sí | Modelo (Foundry: nombre del *deployment*; Ollama: tag) |
| `LLM_API_KEY` | Si `LLM_AUTH=key` | API key estática (Ollama acepta cualquier valor) |
| `LLM_AUTH` | No | `key` (por defecto) o `entra` (token de Microsoft Entra ID) |
| `LLM_TOKEN_SCOPE` | No | Scope para `entra`; por defecto `https://ai.azure.com/.default` |

### Perfiles

**Foundry (Entra ID)**

```
LLM_BASE_URL=https://<recurso>.services.ai.azure.com/api/projects/<proyecto>/openai/v1
LLM_MODEL=<nombre-del-deployment>
LLM_AUTH=entra
```

**Ollama**

```
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=ollama
```

**Otro proveedor con API key**

```
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=<modelo>
LLM_API_KEY=<key>
```

## Uso

```bash
uv run --env-file .env arch-ai-preparation
```

## Validar ejecucion
```bash
echo $?
```

Salida esperada: `Conexión OK · modelo=… · respuesta='OK'`

### Códigos de salida

| Código | Significado |
|---|---|
| 0 | Conexión correcta |
| 1 | Error de credenciales, 404 (URL/modelo) o red |
| 2 | Faltan variables de entorno |

## Solución de problemas

- **401/403 en Foundry**: ejecuta `az login`; verifica el rol *Azure AI User* y el scope.
- **404**: `LLM_BASE_URL` debe terminar en `/openai/v1` (Foundry) o `/v1` (otros); revisa `LLM_MODEL`.
- **Sin conexión (Ollama)**: comprueba que `ollama serve` está activo.

## Desarrollo

```bash
uv run ruff check . && uv run ruff format .
```

Nunca subas `.env` al repositorio (debe estar en `.gitignore`).
