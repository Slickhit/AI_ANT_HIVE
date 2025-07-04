import os
import concurrent.futures
import asyncio
import threading

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

# Event loop running in a background thread for async tasks
_loop = asyncio.new_event_loop()

def _run_loop() -> None:  # pragma: no cover - thread bootstrap
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

_thread = threading.Thread(target=_run_loop, daemon=True)
_thread.start()


async def _chat_task_async(
    messages: list[dict], model: str, max_tokens: int
) -> str | None:
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(
            _executor,
            lambda: openai.ChatCompletion.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
            ),
        )
        return resp.choices[0].message["content"].strip()
    except Exception:
        return None


def chat_completion(
    messages: list[dict], model: str, max_tokens: int = 20
) -> concurrent.futures.Future:
    """Return a future that resolves with the completion text."""

    future: concurrent.futures.Future = concurrent.futures.Future()

    async def runner() -> None:
        result = await _chat_task_async(messages, model, max_tokens)
        future.set_result(result)

    def schedule() -> None:  # pragma: no cover - thread handoff
        asyncio.create_task(runner())

    _loop.call_soon_threadsafe(schedule)
    return future
