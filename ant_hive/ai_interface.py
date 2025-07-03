import os

try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    class _DummyChat:
        @staticmethod
        def create(*_args, **_kwargs):
            raise ModuleNotFoundError("openai is required for this feature")

    class _DummyOpenAI:
        api_key = ""
        ChatCompletion = _DummyChat

    openai = _DummyOpenAI()

openai.api_key = os.getenv("OPENAI_API_KEY", "")


def chat_completion(messages: list[dict], model: str, max_tokens: int = 20) -> str | None:
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message["content"].strip()
    except Exception:
        return None
