"""
Unit tests for scoring service.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock


class TestScoringServiceInit:
    """Test ScoringService initialization."""
    
    def test_service_initialization(self, app):
        """Test that ScoringService initializes correctly."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            
            assert service.app == app
            assert service.max_workers > 0
            assert service.max_retries > 0
    
    def test_lazy_docling_service(self, app):
        """Test lazy initialization of docling service."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            
            # Initially None
            assert service._docling_service is None


class TestProgressUpdate:
    """Test progress update functionality."""
    
    def test_update_progress(self, app):
        """Test _update_progress method."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            progress_store = {}
            
            service._update_progress(progress_store, 1, 'scoring_progress', 5, 10)
            
            assert 1 in progress_store
            assert progress_store[1]['progress'] == 50.0
            assert progress_store[1]['current'] == 5
            assert progress_store[1]['total'] == 10
    
    def test_update_progress_completed(self, app):
        """Test _update_progress with completed status."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            progress_store = {}
            
            service._update_progress(progress_store, 1, 'completed', 10, 10)
            
            assert progress_store[1]['status'] == 'completed'
            assert progress_store[1]['progress'] == 100.0
    
    def test_update_progress_failed(self, app):
        """Test _update_progress with failed status."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            progress_store = {}
            
            service._update_progress(progress_store, 1, 'failed', 0, 0, error='Test error')
            
            assert progress_store[1]['status'] == 'failed'


class TestProcessSingleFile:
    """Test _process_single_file method."""
    
    def test_single_processing_mode_detection(self, app):
        """Test that single processing mode is detected correctly."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            
            # Mock the docling_service to return None (simulating failure)
            service._docling_service = Mock()
            service._docling_service.parse_multiple_documents = Mock(return_value=None)
            service._docling_service.parse_pdf_with_retry = Mock(return_value=None)
            
            # Single processing file_info
            file_info = {
                'original_name': 'Mahasiswa_1',
                'path': '/tmp/test',
                'file_paths': ['/tmp/test/file1.png'],
                'is_single_processing': True
            }
            
            result = service._process_single_file(
                file_info=file_info,
                answer_key_content=None,
                question_content=None,
                additional_notes=None,
                score_min=40,
                score_max=100,
                enable_evaluation=True
            )
            
            # Should return error result
            assert result.get('error') == True
    
    def test_bulk_processing_mode(self, app, sample_pdf):
        """Test bulk processing mode."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            
            # Mock the docling_service
            service._docling_service = Mock()
            service._docling_service.parse_pdf_with_retry = Mock(return_value=None)
            
            file_info = {
                'original_name': 'test_student.pdf',
                'path': str(sample_pdf),
                'is_single_processing': False
            }
            
            result = service._process_single_file(
                file_info=file_info,
                answer_key_content=None,
                question_content=None,
                additional_notes=None,
                score_min=40,
                score_max=100,
                enable_evaluation=True
            )
            
            # Should fail because mock returns None
            assert result.get('error') == True

    def test_worker_process_single_file_has_app_context(self, app, sample_pdf):
        """Worker execution should provide app context for LLM config/database access."""
        from flask import current_app

        class ContextAwareLLM:
            def score_report(self, **kwargs):
                # Accessing current_app would fail without application context.
                assert current_app is not None
                return {
                    'nim': 'TIDAK_DITEMUKAN',
                    'student_name': 'TIDAK_DITEMUKAN',
                    'score': 88,
                    'evaluation': 'ok',
                    'error': False,
                }

        with app.app_context():
            from app.services.scoring_service import ScoringService

            service = ScoringService(app)
            service._docling_service = Mock()
            service._docling_service.parse_pdf_with_retry = Mock(return_value='Isi laporan mahasiswa')
            service._llm_service = ContextAwareLLM()

        # Call outside app_context to emulate worker-thread usage.
        result = service._process_single_file(
            file_info={
                'original_name': 'L200240020_Holizah_Hanufi_A.pdf',
                'path': str(sample_pdf),
                'is_single_processing': False,
            },
            answer_key_content='kunci',
            question_content='soal',
            additional_notes='catatan',
            score_min=40,
            score_max=100,
            enable_evaluation=True,
        )

        assert result['error'] is False
        assert result['score'] == 88

    def test_single_processing_passes_source_filename_to_llm(self, app):
        """Single-processing should pass real uploaded filename into LLM context."""

        class LLMSpy:
            def __init__(self):
                self.captured_filename = None

            def score_report(self, **kwargs):
                self.captured_filename = kwargs.get('source_filename')
                return {
                    'nim': 'TIDAK_DITEMUKAN',
                    'student_name': 'TIDAK_DITEMUKAN',
                    'score': 77,
                    'evaluation': 'ok',
                    'error': False,
                }

        with app.app_context():
            from app.services.scoring_service import ScoringService

            service = ScoringService(app)
            service._docling_service = Mock()
            service._docling_service.parse_multiple_documents = Mock(return_value='Gabungan jawaban')
            spy = LLMSpy()
            service._llm_service = spy

        result = service._process_single_file(
            file_info={
                'original_name': 'Mahasiswa_1',
                'source_filename': 'L200240020_Holizah_Hanufi_A.pdf',
                'path': '/tmp/student_1',
                'file_paths': ['/tmp/student_1/page1.png'],
                'is_single_processing': True,
            },
            answer_key_content='kunci',
            question_content='soal',
            additional_notes='catatan',
            score_min=40,
            score_max=100,
            enable_evaluation=True,
        )

        assert result['error'] is False
        assert spy.captured_filename == 'L200240020_Holizah_Hanufi_A.pdf'


class TestCSVGeneration:
    """Test CSV generation."""
    
    def test_generate_csv(self, app):
        """Test CSV generation with sample results."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            
            # Sample results
            results = [
                {
                    'filename': 'student1.pdf',
                    'nim': 'L200200001',
                    'student_name': 'John Doe',
                    'score': 85,
                    'evaluation': 'Good work'
                },
                {
                    'filename': 'student2.pdf',
                    'nim': 'L200200002',
                    'student_name': 'Jane Doe',
                    'score': 90,
                    'evaluation': 'Excellent'
                }
            ]
            
            csv_path = service._generate_csv(job_id=1, results=results, username='testuser')
            
            assert os.path.exists(csv_path)
            
            # Read and verify content
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                assert 'Status OCR Docling' in content
                assert 'L200200001' in content
                assert 'John Doe' in content
                assert '85' in content
            
            # Cleanup
            os.unlink(csv_path)
    
    def test_generate_csv_with_errors(self, app):
        """Test CSV generation with error results."""
        with app.app_context():
            from app.services.scoring_service import ScoringService
            
            service = ScoringService(app)
            
            results = [
                {
                    'filename': 'student1.pdf',
                    'nim': 'ERROR',
                    'student_name': 'ERROR',
                    'score': None,
                    'evaluation': 'Failed to process',
                    'error': True
                }
            ]
            
            csv_path = service._generate_csv(job_id=1, results=results, username='testuser')
            
            assert os.path.exists(csv_path)

            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                assert 'Status OCR Docling' in content
                assert 'Tidak Diketahui - Status OCR tidak tersedia.' in content
            
            # Cleanup
            os.unlink(csv_path)

    def test_generate_csv_uses_explicit_ocr_status_fields(self, app):
        """CSV should serialize explicit OCR status/detail when provided in result rows."""
        with app.app_context():
            from app.services.scoring_service import ScoringService

            service = ScoringService(app)

            results = [
                {
                    'filename': 'student1.pdf',
                    'nim': 'L200200001',
                    'student_name': 'John Doe',
                    'score': 88,
                    'evaluation': 'OK',
                    'docling_ocr_status': 'OCR Berhasil',
                    'docling_ocr_detail': 'Teks hasil parsing Docling terdeteksi memadai.'
                }
            ]

            csv_path = service._generate_csv(job_id=1, results=results, username='testuser')

            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                assert 'OCR Berhasil - Teks hasil parsing Docling terdeteksi memadai.' in content

            os.unlink(csv_path)


class TestOcrStatusHeuristic:
    """Test OCR success/failure heuristic for Docling parse output."""

    def test_assess_ocr_status_empty_content(self, app):
        with app.app_context():
            from app.services.scoring_service import ScoringService

            service = ScoringService(app)
            status, detail = service._assess_docling_ocr_status('   ')

            assert status == 'OCR Gagal'
            assert 'kosong' in detail.lower()

    def test_assess_ocr_status_placeholder_only_content(self, app):
        with app.app_context():
            from app.services.scoring_service import ScoringService

            service = ScoringService(app)
            status, detail = service._assess_docling_ocr_status('[BASE64_IMAGE_REMOVED] ![](img.png)')

            assert status == 'OCR Gagal'
            assert 'placeholder gambar' in detail.lower()

    def test_assess_ocr_status_short_but_valid_content(self, app):
        with app.app_context():
            from app.services.scoring_service import ScoringService

            service = ScoringService(app)
            status, detail = service._assess_docling_ocr_status('Jawaban: benar 42')

            assert status == 'OCR Berhasil'
            assert 'memadai' in detail.lower()

    def test_assess_ocr_status_normal_text_content(self, app):
        with app.app_context():
            from app.services.scoring_service import ScoringService

            service = ScoringService(app)
            status, detail = service._assess_docling_ocr_status(
                'Mahasiswa menjelaskan algoritma sorting dengan langkah dan contoh output yang lengkap.'
            )

            assert status == 'OCR Berhasil'
            assert 'memadai' in detail.lower()
