"""Tests for LLM settings admin endpoints."""

from app.services.llm_service import LLMService


def test_fetch_models_rejects_unsupported_provider(auth_client):
    """Unsupported provider should return HTTP 400."""
    response = auth_client.post(
        '/admin/llm_settings/fetch-models',
        data={
            'provider': 'unknown-provider',
            'api_key': 'dummy-key',
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error'] == 'Provider tidak didukung'


def test_fetch_models_rejects_non_https_base_url(auth_client):
    """Non-HTTPS base URLs should be rejected to avoid API key leakage."""
    response = auth_client.post(
        '/admin/llm_settings/fetch-models',
        data={
            'provider': 'openai',
            'api_key': 'dummy-key',
            'base_url': 'http://api.openai.com/v1',
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error'] == 'Base URL harus menggunakan HTTPS'


def test_fetch_models_rejects_provider_host_mismatch(auth_client):
    """Provider must only accept base_url hosts that match that provider."""
    response = auth_client.post(
        '/admin/llm_settings/fetch-models',
        data={
            'provider': 'openai',
            'api_key': 'dummy-key',
            'base_url': 'https://openrouter.ai/api/v1',
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error'] == 'Base URL tidak sesuai dengan provider yang dipilih'


def test_fetch_models_success_for_openrouter(auth_client, monkeypatch):
    """Supported provider should return fetched model list."""
    monkeypatch.setattr(
        LLMService,
        'fetch_available_models',
        staticmethod(lambda provider, api_key, base_url: [{'id': 'openai/gpt-4o-mini', 'owned_by': 'openrouter'}]),
    )

    response = auth_client.post(
        '/admin/llm_settings/fetch-models',
        data={
            'provider': 'openrouter',
            'api_key': 'sk-or-test',
            'base_url': 'https://openrouter.ai/api/v1',
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['models'][0]['id'] == 'openai/gpt-4o-mini'


def test_fetch_models_success_for_github(auth_client, monkeypatch):
    """GitHub provider should pass whitelist and return model list."""
    monkeypatch.setattr(
        LLMService,
        'fetch_available_models',
        staticmethod(lambda provider, api_key, base_url: [{'id': 'openai/gpt-4.1-mini', 'owned_by': 'github'}]),
    )

    response = auth_client.post(
        '/admin/llm_settings/fetch-models',
        data={
            'provider': 'github',
            'api_key': 'github_pat_test',
            'base_url': 'https://models.inference.ai.azure.com',
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['models'][0]['id'] == 'openai/gpt-4.1-mini'


def test_save_llm_settings_rejects_missing_api_key(auth_client):
    """Saving non-Gemini provider without API key must be blocked."""
    response = auth_client.post(
        '/admin/llm_settings/',
        data={
            'llm_provider': 'openai',
            'llm_model': 'gpt-4.1',
            'openai_api_key': '',
            'openai_base_url': 'https://api.openai.com/v1',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'wajib diisi'.encode('utf-8') in response.data


def test_save_llm_settings_rejects_provider_host_mismatch(auth_client):
    """Saving settings must reject base_url host that does not match selected provider."""
    response = auth_client.post(
        '/admin/llm_settings/',
        data={
            'llm_provider': 'openai',
            'llm_model': 'gpt-4.1',
            'openai_api_key': 'sk-test',
            'openai_base_url': 'https://openrouter.ai/api/v1',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'tidak sesuai dengan provider'.encode('utf-8') in response.data
