"""API contract and validation tests, without a live Euri AI account."""

from fastapi.testclient import TestClient

import main
from ai_engine import AIProviderError, ConfigurationError

client = TestClient(main.app)


def test_service_info_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/").json()["docs"] == "/docs"
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_explain_route(monkeypatch):
    monkeypatch.setattr(main, "explain_code", lambda language, topic, level: "Example")
    response = client.post(
        "/explain", json={"language": "Python", "topic": "recursion", "level": "Beginner"}
    )
    assert response.status_code == 200
    assert response.json() == {"response": "Example"}


def test_debug_route_passes_code_and_context(monkeypatch):
    received = {}

    def stub(language, code, context):
        received.update(language=language, code=code, context=context)
        return "Suggested fix"

    monkeypatch.setattr(main, "debug_code", stub)
    response = client.post(
        "/debug",
        json={"language": "Python", "code": "print(x)", "context": "NameError"},
    )
    assert response.status_code == 200
    assert response.json() == {"response": "Suggested fix"}
    assert received == {"language": "Python", "code": "print(x)", "context": "NameError"}


def test_generate_route(monkeypatch):
    monkeypatch.setattr(main, "generate_code", lambda language, topic, level: "New example")
    response = client.post(
        "/generate",
        json={"language": "Go", "topic": "hello world", "level": "Intermediate"},
    )
    assert response.status_code == 200
    assert response.json()["response"] == "New example"


def test_invalid_language_rejected():
    response = client.post(
        "/explain", json={"language": "COBOL", "topic": "loops", "level": "Beginner"}
    )
    assert response.status_code == 422


def test_missing_actual_code_rejected():
    response = client.post("/debug", json={"language": "Python", "topic": "loops"})
    assert response.status_code == 422


def test_extra_fields_rejected():
    response = client.post(
        "/generate",
        json={"language": "Python", "topic": "loops", "level": "Beginner", "token": "abc"},
    )
    assert response.status_code == 422


def test_missing_key_returns_503_without_exception_details(monkeypatch):
    def fail(*_args):
        raise ConfigurationError("Internal configuration details")

    monkeypatch.setattr(main, "explain_code", fail)
    response = client.post(
        "/explain", json={"language": "Python", "topic": "loops", "level": "Beginner"}
    )
    assert response.status_code == 503
    assert "Internal configuration details" not in response.text


def test_upstream_failure_returns_502(monkeypatch):
    def fail(*_args):
        raise AIProviderError("Sensitive provider metadata")

    monkeypatch.setattr(main, "generate_code", fail)
    response = client.post(
        "/generate", json={"language": "Python", "topic": "loops", "level": "Beginner"}
    )
    assert response.status_code == 502
    assert "Sensitive provider metadata" not in response.text


def test_debug_preserves_source_indentation(monkeypatch):
    received = {}

    def stub(language, code, context):
        received["code"] = code
        return "OK"

    monkeypatch.setattr(main, "debug_code", stub)
    source = "    print(42)\n"
    response = client.post("/debug", json={"language": "Python", "code": source})
    assert response.status_code == 200
    assert received["code"] == source


def test_whitespace_only_source_rejected():
    response = client.post("/debug", json={"language": "Python", "code": "    "})
    assert response.status_code == 422
