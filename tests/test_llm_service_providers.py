"""Tests for OpenAI-compatible provider support in LLMService."""

from flask import current_app

from app.models import LLMConfig
from app.services.llm_service import LLMService


def test_deepseek_provider_uses_provider_default_model(app):
    """If model is unset, provider-specific default should be used."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'deepseek')
        LLMConfig.set('llm_model', '')
        LLMConfig.set('deepseek_api_key', 'sk-deepseek-test')
        LLMConfig.set('deepseek_base_url', 'https://api.deepseek.com/v1')

        service = LLMService(current_app.config)
        cfg = service._get_active_config()

        assert cfg['provider'] == 'deepseek'
        assert cfg['model'] == 'deepseek-chat'
        assert cfg['deepseek_api_key'] == 'sk-deepseek-test'
        assert cfg['deepseek_base_url'] == 'https://api.deepseek.com/v1'


def test_openrouter_status_reads_key_and_base_url(app):
    """Status for OpenAI-compatible providers should expose key presence and base URL."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'openrouter')
        LLMConfig.set('llm_model', 'openai/gpt-4o-mini')
        LLMConfig.set('openrouter_api_key', 'sk-or-test')
        LLMConfig.set('openrouter_base_url', 'https://openrouter.ai/api/v1')

        service = LLMService(current_app.config)
        status = service.get_status()

        assert status['provider'] == 'openrouter'
        assert status['has_api_key'] is True
        assert status['base_url'] == 'https://openrouter.ai/api/v1'


def test_siliconflow_missing_key_returns_user_friendly_error(app):
    """Scoring should fail early with clear message when SiliconFlow API key is absent."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'siliconflow')
        LLMConfig.set('llm_model', 'Qwen/Qwen2.5-72B-Instruct')
        LLMConfig.set('siliconflow_api_key', '')
        LLMConfig.set('siliconflow_base_url', 'https://api.siliconflow.cn/v1')

        service = LLMService(current_app.config)
        result = service.score_report('Contoh laporan mahasiswa')

        assert result['error'] is True
        assert 'SILICONFLOW' in result['evaluation']


def test_github_provider_uses_defaults_and_status(app):
    """GitHub provider should resolve default model/base URL and expose ready status."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'github')
        LLMConfig.set('llm_model', '')
        LLMConfig.set('github_api_key', 'github_pat_test')
        LLMConfig.set('github_base_url', '')

        service = LLMService(current_app.config)
        cfg = service._get_active_config()
        status = service.get_status()

        assert cfg['provider'] == 'github'
        assert cfg['model'] == 'openai/gpt-4.1-mini'
        assert cfg['github_base_url'] == 'https://models.github.ai/inference'
        assert status['provider'] == 'github'
        assert status['has_api_key'] is True


def test_db_empty_provider_key_overrides_env_key(app):
    """Explicit empty DB key must not fall back to env/app-config key."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'openai')
        LLMConfig.set('openai_api_key', '')
        current_app.config['OPENAI_API_KEY'] = 'env-key-should-not-win'

        service = LLMService(current_app.config)
        cfg = service._get_active_config()

        assert cfg['provider'] == 'openai'
        assert cfg['openai_api_key'] == ''


def test_filename_fallback_populates_identity_when_model_missing_fields(app, monkeypatch):
    """If model cannot find identity, filename fallback should populate NIM/name."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'gemini')
        LLMConfig.set('gemini_api_keys', '["test-gemini-key"]')

        service = LLMService(current_app.config)

        def fake_score_with_gemini(*args, **kwargs):
            return {
                'nim': 'TIDAK_DITEMUKAN',
                'student_name': 'TIDAK_DITEMUKAN',
                'score': 82,
                'evaluation': 'Jawaban baik',
                'error': False,
            }

        monkeypatch.setattr(service, '_score_with_gemini', fake_score_with_gemini)

        result = service.score_report(
            student_content='Isi laporan mahasiswa',
            source_filename='HOLIZAH_HANUFI_1159403_assignsubmission_file_L200240020_Holizah Hanufi_A.pdf',
        )

        assert result['nim'] == 'L200240020'
        assert result['student_name'] == 'Holizah Hanufi'


def test_filename_fallback_does_not_override_valid_model_identity(app, monkeypatch):
    """Filename fallback should keep model-provided NIM/name when already valid."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'gemini')
        LLMConfig.set('gemini_api_keys', '["test-gemini-key"]')

        service = LLMService(current_app.config)

        def fake_score_with_gemini(*args, **kwargs):
            return {
                'nim': 'L200111222',
                'student_name': 'Nama Dari Dokumen',
                'score': 90,
                'evaluation': 'Sangat baik',
                'error': False,
            }

        monkeypatch.setattr(service, '_score_with_gemini', fake_score_with_gemini)

        result = service.score_report(
            student_content='Isi laporan mahasiswa',
            source_filename='L200240020_Holizah_Hanufi_A.pdf',
        )

        assert result['nim'] == 'L200111222'
        assert result['student_name'] == 'Nama Dari Dokumen'


def test_filename_fallback_ignores_unlabeled_numeric_tokens(app, monkeypatch):
    """Date/timestamp-like numeric tokens should not be used as NIM fallback."""
    with app.app_context():
        LLMConfig.set('llm_provider', 'gemini')
        LLMConfig.set('gemini_api_keys', '["test-gemini-key"]')

        service = LLMService(current_app.config)

        def fake_score_with_gemini(*args, **kwargs):
            return {
                'nim': 'TIDAK_DITEMUKAN',
                'student_name': 'TIDAK_DITEMUKAN',
                'score': 75,
                'evaluation': 'cukup',
                'error': False,
            }

        monkeypatch.setattr(service, '_score_with_gemini', fake_score_with_gemini)

        result = service.score_report(
            student_content='Isi laporan mahasiswa',
            source_filename='IMG_20260101_12345678_report_final.pdf',
        )

        assert result['nim'] == 'TIDAK_DITEMUKAN'
