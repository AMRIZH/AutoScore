"""Runtime settings persistence and synchronization helpers."""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import LLMConfig


RUNTIME_CONFIG_KEYS = {
    'max_file_size_mb': 'runtime_max_file_size_mb',
    'max_pdf_count': 'runtime_max_pdf_count',
    'enable_ocr': 'runtime_enable_ocr',
    'enable_cleanup': 'runtime_enable_cleanup',
}


def _parse_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    lowered = str(value).strip().lower()
    if lowered in {'1', 'true', 'yes', 'on'}:
        return True
    if lowered in {'0', 'false', 'no', 'off'}:
        return False
    return default


def read_runtime_settings(config: dict) -> dict:
    """Read runtime settings from DB and fallback to current config values."""
    default_max_file_size_mb = max(1, _parse_int(config.get('MAX_FILE_SIZE_MB', 10), 10))
    default_max_pdf_count = max(1, _parse_int(config.get('MAX_PDF_COUNT', 50), 50))
    default_enable_ocr = _parse_bool(config.get('ENABLE_OCR', True), True)
    default_enable_cleanup = _parse_bool(config.get('ENABLE_CLEANUP', True), True)

    runtime_keys = set(RUNTIME_CONFIG_KEYS.values())
    rows = LLMConfig.query.filter(LLMConfig.key.in_(runtime_keys)).all()
    values_by_key = {row.key: row.value for row in rows}

    max_file_size_mb = max(
        1,
        _parse_int(values_by_key.get(RUNTIME_CONFIG_KEYS['max_file_size_mb']), default_max_file_size_mb),
    )
    max_pdf_count = max(
        1,
        _parse_int(values_by_key.get(RUNTIME_CONFIG_KEYS['max_pdf_count']), default_max_pdf_count),
    )
    enable_ocr = _parse_bool(
        values_by_key.get(RUNTIME_CONFIG_KEYS['enable_ocr']),
        default_enable_ocr,
    )
    enable_cleanup = _parse_bool(
        values_by_key.get(RUNTIME_CONFIG_KEYS['enable_cleanup']),
        default_enable_cleanup,
    )

    # MAX_CONTENT_LENGTH is request-wide in Flask/Werkzeug, so derive it from
    # max file size * max number of files (+ small multipart overhead buffer).
    request_size_mb = max_file_size_mb * max_pdf_count + 1

    return {
        'MAX_FILE_SIZE_MB': max_file_size_mb,
        'MAX_CONTENT_LENGTH': request_size_mb * 1024 * 1024,
        'MAX_PDF_COUNT': max_pdf_count,
        'ENABLE_OCR': enable_ocr,
        'ENABLE_CLEANUP': enable_cleanup,
    }


def apply_runtime_settings(config: dict, settings: dict) -> None:
    """Apply resolved runtime settings to Flask app config."""
    config['MAX_FILE_SIZE_MB'] = settings['MAX_FILE_SIZE_MB']
    config['MAX_CONTENT_LENGTH'] = settings['MAX_CONTENT_LENGTH']
    config['MAX_PDF_COUNT'] = settings['MAX_PDF_COUNT']
    config['ENABLE_OCR'] = settings['ENABLE_OCR']
    config['ENABLE_CLEANUP'] = settings['ENABLE_CLEANUP']


def sync_runtime_settings(config: dict) -> dict:
    """Load settings from DB and apply them to app config."""
    settings = read_runtime_settings(config)
    apply_runtime_settings(config, settings)
    return settings


def persist_runtime_settings(max_file_size_mb: int, max_pdf_count: int, enable_ocr: bool, enable_cleanup: bool) -> None:
    """Persist runtime settings in DB so every worker can read consistent values."""
    payload = {
        RUNTIME_CONFIG_KEYS['max_file_size_mb']: str(max_file_size_mb),
        RUNTIME_CONFIG_KEYS['max_pdf_count']: str(max_pdf_count),
        RUNTIME_CONFIG_KEYS['enable_ocr']: '1' if enable_ocr else '0',
        RUNTIME_CONFIG_KEYS['enable_cleanup']: '1' if enable_cleanup else '0',
    }

    try:
        for key, value in payload.items():
            db.session.merge(LLMConfig(key=key, value=value))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
