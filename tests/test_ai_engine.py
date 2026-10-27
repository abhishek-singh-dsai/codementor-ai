"""Provider-independent unit tests for prompts and response normalization."""

import pytest

import ai_engine


class FakeClient:
    def __init__(self, response=None, failure=None):
        self.response = response or {"choices": [{"message": {"content": "  Sample reply  "}}]}
        self.failure = failure
        self.calls = []

    def generate_completion(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure is not None:
            raise self.failure
        return self.response


def test_explain_uses_language_topic_and_level(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(ai_engine, "get_client", lambda: fake)

    result = ai_engine.explain_code("Python", "list comprehensions", "Beginner")

    assert result == "Sample reply"
    assert "list comprehensions" in fake.calls[0]["prompt"]
    assert "Python" in fake.calls[0]["prompt"]
    assert "beginner" in fake.calls[0]["prompt"]


def test_debug_receives_actual_source_code(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(ai_engine, "get_client", lambda: fake)

    ai_engine.debug_code("Python", "print(x)", "NameError")

    assert "print(x)" in fake.calls[0]["prompt"]
    assert "NameError" in fake.calls[0]["prompt"]
    assert "do not execute" in fake.calls[0]["prompt"].lower()


def test_generate_explains_usage(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(ai_engine, "get_client", lambda: fake)

    ai_engine.generate_code("Go", "read a file", "Intermediate")

    assert "read a file" in fake.calls[0]["prompt"]
    assert "How to run" in fake.calls[0]["prompt"]


@pytest.mark.parametrize(
    "response",
    [{"choices": []}, {"unexpected": "format"}, {"choices": [{"message": {"content": " "}}]}],
)
def test_invalid_provider_response_is_handled(monkeypatch, response):
    monkeypatch.setattr(ai_engine, "get_client", lambda: FakeClient(response=response))

    with pytest.raises(ai_engine.AIProviderError):
        ai_engine.explain_code("Python", "loops", "Beginner")


def test_upstream_error_is_sanitized(monkeypatch):
    fake = FakeClient(failure=RuntimeError("secret upstream error"))
    monkeypatch.setattr(ai_engine, "get_client", lambda: fake)

    with pytest.raises(ai_engine.AIProviderError, match="could not complete") as error:
        ai_engine.generate_code("Python", "a list", "Beginner")
    assert "secret upstream error" not in str(error.value)


def test_missing_credentials_fail_cleanly(monkeypatch):
    monkeypatch.delenv("EURIAI_API_KEY", raising=False)
    ai_engine.get_client.cache_clear()

    with pytest.raises(ai_engine.ConfigurationError, match="EURIAI_API_KEY"):
        ai_engine.get_client()
