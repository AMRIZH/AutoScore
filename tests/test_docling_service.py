"""Unit tests for DoclingService behavior independent of Docling runtime."""

from unittest.mock import Mock

from app.services.docling_service import DoclingService


def test_parse_image_output_removes_embedded_base64(tmp_path):
    """Image parsing output must not include embedded base64 payloads."""
    image_path = tmp_path / 'sample.png'
    image_path.write_bytes(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )

    service = DoclingService(enable_ocr=True, use_gpu=False)
    service._initialized = True

    mock_document = Mock()
    mock_document.export_to_markdown.return_value = (
        'Hasil OCR awal\n'
        '![img](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ)\n'
        'Akhir dokumen'
    )
    mock_result = Mock(document=mock_document)
    service._converter = Mock(convert=Mock(return_value=mock_result))

    output = service.parse_image(str(image_path))

    assert output is not None
    assert output.startswith('Hasil OCR awal')
    assert 'data:image/png;base64' not in output
    assert '[BASE64_IMAGE_REMOVED]' in output
    assert 'Akhir dokumen' in output
