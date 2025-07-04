import os
import concurrent.futures

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


_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _chat_task(messages: list[dict], model: str, max_tokens: int) -> str | None:
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message["content"].strip()
    except Exception:
        return None


def chat_completion(
    messages: list[dict], model: str, max_tokens: int = 20
) -> concurrent.futures.Future:
    """Return a future that resolves with the completion text."""
    return _executor.submit(_chat_task, messages, model, max_tokens)
