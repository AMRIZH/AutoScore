"""
Scoring service for AutoScoring application.
Orchestrates PDF parsing, LLM scoring, and CSV generation.
"""

import os
import csv
import re
import logging
import threading
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from queue import Queue

from app.extensions import db
from app.models import Job, JobResult, SystemLog, utc_now_naive

logger = logging.getLogger(__name__)


DOCILING_IMAGE_PLACEHOLDER_PATTERNS = [
    re.compile(r'\[BASE64_IMAGE_REMOVED\]', re.IGNORECASE),
    re.compile(r'!\[[^\]]*\]\([^\)]*\)', re.IGNORECASE),
    re.compile(r'<img[^>]*>', re.IGNORECASE),
    re.compile(r'<!--\s*image[^>]*-->', re.IGNORECASE),
]


class ScoringService:
    """Service for orchestrating the scoring process."""
    
    # Progress messages in Bahasa Indonesia
    PROGRESS_MESSAGES = {
        'uploading': 'Mengunggah dokumen...',
        'reading': 'Membaca laporan...',
        'reading_answer': 'Membaca kunci jawaban...',
        'scoring': 'Menilai tugas mahasiswa...',
        'scoring_progress': 'Menilai laporan {current} dari {total}...',
        'generating': 'Menyusun hasil...',
        'almost_done': 'Hampir selesai...',
        'completed': 'Selesai!',
        'failed': 'Terjadi kesalahan: {error}'
    }
    
    def __init__(self, app):
        """Initialize scoring service with Flask app context."""
        self.app = app
        self.config = app.config
        self.max_workers = app.config.get('MAX_WORKERS', 4)
        self.max_retries = app.config.get('MAX_RETRIES', 3)
        
        # Initialize services lazily
        self._docling_service = None
        self._llm_service = None
        self._docling_lock = threading.Lock()
        self._llm_lock = threading.Lock()
        
        # Queue for database updates (thread-safe)
        self._db_update_queue = Queue()
    
    @property
    def docling_service(self):
        """Lazy initialization of Docling service (thread-safe)."""
        if self._docling_service is None:
            with self._docling_lock:
                if self._docling_service is None:
                    from app.services.docling_service import DoclingService
                    self._docling_service = DoclingService(
                        enable_ocr=self.config.get('ENABLE_OCR', True),
                        use_gpu=True  # Auto-detect
                    )
        return self._docling_service
    
    @property
    def llm_service(self):
        """Lazy initialization of unified LLM service (thread-safe)."""
        if self._llm_service is None:
            with self._llm_lock:
                if self._llm_service is None:
                    from app.services.llm_service import LLMService
                    self._llm_service = LLMService(self.config)
        return self._llm_service
    
    def start_scoring(
        self,
        job_id: int,
        job_folder: str,
        saved_files: List[Dict],
        progress_store: Dict
    ):
        """
        Start scoring process in background thread.
        
        Args:
            job_id: Database job ID
            job_folder: Path to job's upload folder
            saved_files: List of saved file info dicts
            progress_store: Shared dict to update progress
        """
        is_testing_env = str(os.environ.get('FLASK_TESTING', '')).strip().lower() in {
            '1', 'true', 'yes', 'on'
        }

        # In tests we avoid async background DB writes because fixture teardown
        # can remove temporary sqlite files while daemon threads are still running.
        if self.app.config.get('TESTING') or is_testing_env:
            progress_store[job_id] = {
                'status': 'pending',
                'message': 'Mode test: background scoring dilewati.',
                'progress': 0,
                'total': len(saved_files),
                'current': 0,
            }
            logger.info(
                f"[TEST] Background scoring dilewati untuk job {job_id} (testing mode)"
            )
            return

        thread = threading.Thread(
            target=self._run_scoring,
            args=(job_id, job_folder, saved_files, progress_store),
            daemon=True,
            name=f"ScoringThread-Job{job_id}"
        )
        thread.start()
        logger.info(f"[START] Scoring thread dimulai untuk job {job_id} (thread: {thread.name})")
    
    def _run_scoring(
        self,
        job_id: int,
        job_folder: str,
        saved_files: List[Dict],
        progress_store: Dict
    ):
        """Run the scoring process."""
        start_time = time.time()
        
        with self.app.app_context():
            try:
                # Get job from database
                job = db.session.get(Job, job_id)
                if not job:
                    logger.error(f"[ERROR] Job {job_id} tidak ditemukan di database")
                    return
                
                total_files = len(saved_files)
                logger.info(f"[INFO] Job {job_id}: Memproses {total_files} file PDF")
                logger.info(f"[INFO] Folder: {job_folder}")
                
                # Update job status
                job.status = 'processing'
                job.started_at = utc_now_naive()
                db.session.commit()
                logger.info(f"[OK] Job {job_id} status diubah ke 'processing'")
                
                # Update progress
                self._update_progress(progress_store, job_id, 'reading', 0, total_files)
                
                # Parse answer key if provided
                answer_key_content = None
                if job.answer_key_path and os.path.exists(job.answer_key_path):
                    logger.info(f"[INFO] Membaca kunci jawaban: {job.answer_key_path}")
                    self._update_progress(progress_store, job_id, 'reading_answer', 0, total_files)
                    
                    answer_key_start = time.time()
                    answer_key_content = self.docling_service.parse_pdf_with_retry(
                        job.answer_key_path,
                        max_retries=self.max_retries
                    )
                    answer_key_time = time.time() - answer_key_start
                    
                    if answer_key_content:
                        logger.info(f"[OK] Kunci jawaban berhasil dibaca ({len(answer_key_content)} chars) dalam {answer_key_time:.2f}s")
                    else:
                        logger.warning(f"[WARN] Gagal membaca kunci jawaban untuk job {job_id}")
                else:
                    logger.info(f"[INFO] Job {job_id}: Tidak ada kunci jawaban yang disediakan")
                
                # Parse plain-text question and question documents if provided.
                question_parts = []
                question_content = None

                if job.question_text:
                    question_text = job.question_text.strip()
                    if question_text:
                        question_parts.append("=== SOAL/TUGAS DARI INPUT TEKS WEB ===\n" + question_text)
                        logger.info(
                            f"[INFO] Job {job_id}: Teks soal langsung ditemukan ({len(question_text)} chars)"
                        )

                if job.question_doc_paths:
                    import json as json_module
                    try:
                        question_paths = json_module.loads(job.question_doc_paths)
                        if question_paths:
                            logger.info(f"[INFO] Membaca {len(question_paths)} dokumen soal/tugas")

                            question_start = time.time()
                            question_docs_content = self.docling_service.parse_multiple_documents(question_paths)
                            question_time = time.time() - question_start

                            if question_docs_content:
                                question_parts.append(question_docs_content)
                                logger.info(
                                    f"[OK] Dokumen soal berhasil dibaca ({len(question_docs_content)} chars) dalam {question_time:.2f}s"
                                )
                            else:
                                logger.warning(f"[WARN] Gagal membaca dokumen soal untuk job {job_id}")
                    except json_module.JSONDecodeError as e:
                        logger.error(f"[ERROR] Gagal parsing question_doc_paths JSON: {e}")
                else:
                    logger.info(f"[INFO] Job {job_id}: Tidak ada dokumen soal yang disediakan")

                if question_parts:
                    question_content = "\n\n--- DOKUMEN SOAL/TUGAS ---\n\n".join(question_parts)
                
                # Get additional notes
                additional_notes = job.additional_notes
                if additional_notes:
                    logger.info(f"[INFO] Job {job_id}: Catatan tambahan ditemukan ({len(additional_notes)} chars)")
                
                # Process student files with ThreadPoolExecutor
                results = []
                processed_count = 0
                success_count = 0
                error_count = 0
                
                logger.info(f"[PROCESSING] Memulai pemrosesan {total_files} file dengan {self.max_workers} workers...")
                
                # Process files and collect results
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all tasks
                    future_to_file = {}
                    for idx, file_info in enumerate(saved_files, 1):
                        logger.info(f"[QUEUE] [{idx}/{total_files}] Menjadwalkan: {file_info['original_name']}")
                        future = executor.submit(
                            self._process_single_file,
                            file_info,
                            answer_key_content,
                            question_content,
                            additional_notes,
                            job.score_min,
                            job.score_max,
                            job.enable_evaluation
                        )
                        future_to_file[future] = file_info
                    
                    # Process results as they complete
                    for future in as_completed(future_to_file):
                        file_info = future_to_file[future]
                        processed_count += 1
                        filename = file_info['original_name']
                        
                        # Update progress
                        self._update_progress(
                            progress_store, job_id,
                            'scoring_progress',
                            processed_count, total_files
                        )
                        
                        try:
                            result = future.result()
                            result['filename'] = filename
                            results.append(result)
                            
                            # Log result summary
                            if result.get('error'):
                                error_count += 1
                                logger.error(f"[FAIL] [{processed_count}/{total_files}] {filename}: ERROR - {result.get('evaluation', 'Unknown error')}")
                            else:
                                success_count += 1
                                nim = result.get('nim', 'N/A')
                                name = result.get('student_name', 'N/A')
                                score = result.get('score', 'N/A')
                                logger.info(f"[DONE] [{processed_count}/{total_files}] {filename}: NIM={nim}, Nama={name}, Skor={score}")
                            
                            # Update JobResult in database (within app context)
                            self._update_job_result_in_db(
                                job_id, filename, result
                            )
                            
                            # Update job processed count
                            job.processed_files = processed_count
                            db.session.commit()
                            
                        except Exception as e:
                            error_count += 1
                            error_msg = str(e)
                            logger.error(f"[FAIL] [{processed_count}/{total_files}] {filename}: EXCEPTION - {error_msg}")
                            logger.debug(traceback.format_exc())
                            
                            error_result = {
                                'filename': filename,
                                'nim': 'ERROR',
                                'student_name': 'ERROR',
                                'score': None,
                                'evaluation': f'Error: {error_msg}',
                                'error': True
                            }
                            results.append(error_result)
                            
                            # Update JobResult with error
                            self._update_job_result_in_db(
                                job_id, filename, error_result
                            )
                            
                            job.processed_files = processed_count
                            db.session.commit()
                
                # Processing summary
                elapsed_time = time.time() - start_time
                logger.info(f"[SUMMARY] Job {job_id} - Ringkasan Pemrosesan:")
                logger.info(f"   - Total file: {total_files}")
                logger.info(f"   - Berhasil: {success_count}")
                logger.info(f"   - Error: {error_count}")
                logger.info(f"   - Waktu: {elapsed_time:.2f}s")
                
                # Update progress
                self._update_progress(progress_store, job_id, 'generating', total_files, total_files)
                
                # Generate CSV
                logger.info(f"[CSV] Membuat file CSV untuk job {job_id}...")
                csv_path = self._generate_csv(job_id, results, job.user.username)
                logger.info(f"[OK] File CSV dibuat: {csv_path}")
                
                # Update job as completed
                job.status = 'completed'
                job.result_csv_path = csv_path
                job.completed_at = utc_now_naive()
                job.status_message = f'Berhasil menilai {success_count}/{total_files} laporan'
                db.session.commit()
                logger.info(f"[OK] Job {job_id} status diubah ke 'completed'")
                
                # Update progress
                self._update_progress(progress_store, job_id, 'completed', total_files, total_files)
                
                # Log completion
                SystemLog.log(
                    'INFO', 'scoring',
                    f'Job {job_id} selesai: {success_count}/{total_files} file berhasil dinilai dalam {elapsed_time:.2f}s',
                    user_id=job.user_id
                )
                
                logger.info(f"[COMPLETE] Job {job_id} SELESAI dalam {elapsed_time:.2f} detik")
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                error_msg = str(e)
                logger.error(f"[FATAL] FATAL ERROR Job {job_id}: {error_msg}")
                logger.error(traceback.format_exc())
                
                # Update job as failed
                try:
                    job = db.session.get(Job, job_id)
                    if job:
                        job.status = 'failed'
                        job.status_message = error_msg
                        job.completed_at = utc_now_naive()
                        db.session.commit()
                        logger.info(f"[OK] Job {job_id} status diubah ke 'failed'")
                except Exception as db_error:
                    logger.error(f"[ERROR] Gagal update status job: {db_error}")
                
                # Update progress
                self._update_progress(
                    progress_store, job_id, 'failed',
                    0, 0, error=error_msg
                )
                
                # Log error
                SystemLog.log(
                    'ERROR', 'scoring',
                    f'Job {job_id} gagal setelah {elapsed_time:.2f}s: {error_msg}',
                    user_id=job.user_id if job else None
                )
    
    def _process_single_file(
        self,
        file_info: Dict,
        answer_key_content: Optional[str],
        question_content: Optional[str],
        additional_notes: Optional[str],
        score_min: int,
        score_max: int,
        enable_evaluation: bool
    ) -> Dict[str, Any]:
        """
        Process a single student file or multiple files for single processing.
        
        Note: This runs in a worker thread, so NO database operations here!
        Return results to be processed in main thread.
        """
        with self.app.app_context():
            filename = file_info['original_name']
            thread_name = threading.current_thread().name

            start_time = time.time()
            logger.debug(f"[{thread_name}] [FILE] Memproses: {filename}")

            # Check if this is single processing mode (multiple files per student)
            is_single_processing = file_info.get('is_single_processing', False)

            parse_start = time.time()
            student_content = None

            if is_single_processing:
                # Single processing mode: parse multiple files and combine
                file_paths = file_info.get('file_paths', [])

                if not file_paths:
                    error_msg = 'Tidak ada file untuk diproses'
                    logger.error(f"[{thread_name}] [FAIL] {filename}: {error_msg}")
                    return {
                        'nim': file_info.get('nim', 'ERROR'),
                        'student_name': file_info.get('name', 'ERROR'),
                        'score': None,
                        'evaluation': error_msg,
                        'error': True,
                        'docling_ocr_status': 'OCR Gagal',
                        'docling_ocr_detail': 'Docling gagal memproses seluruh file jawaban.',
                        'parse_time': 0,
                        'score_time': 0
                    }

                logger.debug(f"[{thread_name}] [PARSE] Parsing {len(file_paths)} files untuk {filename}")

                # Parse all files and combine content
                combined_content = self.docling_service.parse_multiple_documents(file_paths)

                if combined_content:
                    student_content = combined_content
                    logger.debug(f"[{thread_name}] [OK] Combined content: {len(student_content)} chars")
                else:
                    error_msg = 'Gagal membaca file-file jawaban'
                    parse_time = time.time() - parse_start
                    logger.error(f"[{thread_name}] [FAIL] {filename}: {error_msg} ({parse_time:.2f}s)")

                    return {
                        'nim': file_info.get('nim', 'ERROR'),
                        'student_name': file_info.get('name', 'ERROR'),
                        'score': None,
                        'evaluation': error_msg,
                        'error': True,
                        'docling_ocr_status': 'OCR Gagal',
                        'docling_ocr_detail': 'Docling gagal memproses seluruh file jawaban.',
                        'parse_time': parse_time,
                        'score_time': 0
                    }
            else:
                # Bulk processing mode: single PDF file
                filepath = file_info['path']
                logger.debug(f"[{thread_name}] [PARSE] Parsing PDF: {filename}")

                student_content = self.docling_service.parse_pdf_with_retry(
                    filepath,
                    max_retries=self.max_retries
                )

            parse_time = time.time() - parse_start

            if not student_content:
                if is_single_processing:
                    error_msg = 'Gagal membaca file-file jawaban'
                else:
                    error_msg = f'Gagal membaca file setelah {self.max_retries} percobaan'
                logger.error(f"[{thread_name}] [FAIL] {filename}: {error_msg} ({parse_time:.2f}s)")

                return {
                    'nim': file_info.get('nim', 'ERROR'),
                    'student_name': file_info.get('name', 'ERROR'),
                    'score': None,
                    'evaluation': error_msg,
                    'error': True,
                    'docling_ocr_status': 'OCR Gagal',
                    'docling_ocr_detail': 'Docling tidak menghasilkan konten yang bisa diproses.',
                    'parse_time': parse_time,
                    'score_time': 0
                }

            content_length = len(student_content)
            ocr_status, ocr_detail = self._assess_docling_ocr_status(student_content)
            logger.debug(f"[{thread_name}] [OK] Content parsed: {filename} ({content_length} chars, {parse_time:.2f}s)")

            # Step 2: Score with LLM
            score_start = time.time()
            logger.debug(f"[{thread_name}] [LLM] Menilai dengan LLM: {filename}")

            result = self.llm_service.score_report(
                student_content=student_content,
                answer_key_content=answer_key_content,
                question_content=question_content,
                additional_notes=additional_notes,
                score_min=score_min,
                score_max=score_max,
                enable_evaluation=enable_evaluation,
                source_filename=file_info.get('source_filename') or filename,
            )

            score_time = time.time() - score_start
            total_time = time.time() - start_time

            result['parse_time'] = parse_time
            result['score_time'] = score_time
            result['total_time'] = total_time
            result['content_length'] = content_length
            result['docling_ocr_status'] = ocr_status
            result['docling_ocr_detail'] = ocr_detail

            if result.get('error'):
                logger.debug(f"[{thread_name}] [FAIL] LLM scoring failed: {filename} ({score_time:.2f}s)")
            else:
                logger.debug(f"[{thread_name}] [OK] LLM scoring done: {filename} - Score: {result.get('score')} ({score_time:.2f}s)")

            logger.debug(f"[{thread_name}] [TIME] Total: {filename} dalam {total_time:.2f}s (parse: {parse_time:.2f}s, score: {score_time:.2f}s)")

            return result

    def _assess_docling_ocr_status(self, content: Optional[str]) -> tuple[str, str]:
        """Assess whether Docling/OCR extracted meaningful text or mostly image placeholders."""
        if not content or not content.strip():
            return 'OCR Gagal', 'Docling menghasilkan konten kosong.'

        normalized = content
        placeholder_detected = any(pattern.search(normalized) for pattern in DOCILING_IMAGE_PLACEHOLDER_PATTERNS)

        # Remove common placeholder/image markers and markdown separators.
        cleaned = normalized
        for pattern in DOCILING_IMAGE_PLACEHOLDER_PATTERNS:
            cleaned = pattern.sub(' ', cleaned)
        cleaned = re.sub(r'---\s*Dokumen:[^-]+---', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[`*_#>|\-]', ' ', cleaned)

        # Keep only alphanumeric signal to estimate readable OCR output.
        text_signal = re.sub(r'[^\w]+', '', cleaned, flags=re.UNICODE)
        word_count = len(re.findall(r'\w+', cleaned, flags=re.UNICODE))
        placeholder_chars = 0
        for pattern in DOCILING_IMAGE_PLACEHOLDER_PATTERNS:
            placeholder_chars += sum(len(match.group(0)) for match in pattern.finditer(normalized))
        placeholder_ratio = placeholder_chars / max(len(normalized), 1)

        # Mark as failed only when evidence strongly points to image-only/failed OCR output.
        if placeholder_detected and (placeholder_ratio >= 0.4 and word_count < 5):
            return 'OCR Gagal', 'Output Docling didominasi placeholder gambar tanpa teks bermakna.'
        if len(text_signal) < 10 and word_count < 3:
            return 'OCR Gagal', 'Teks hasil OCR terlalu sedikit untuk dinilai andal.'

        return 'OCR Berhasil', 'Teks hasil parsing Docling terdeteksi memadai.'
    
    def _update_job_result_in_db(
        self,
        job_id: int,
        filename: str,
        result: Dict[str, Any]
    ):
        """
        Update JobResult in database.
        
        Note: This must be called from within app_context!
        """
        try:
            job_result = JobResult.query.filter_by(
                job_id=job_id,
                filename=filename
            ).first()
            
            if job_result:
                job_result.nim = result.get('nim', 'TIDAK_DITEMUKAN')
                job_result.student_name = result.get('student_name', 'TIDAK_DITEMUKAN')
                job_result.score = result.get('score')
                job_result.evaluation = result.get('evaluation', '')
                job_result.status = 'error' if result.get('error') else 'completed'
                job_result.error_message = result.get('evaluation') if result.get('error') else None
                job_result.processed_at = utc_now_naive()
                db.session.commit()
                logger.debug(f"[OK] JobResult updated: {filename} (status: {job_result.status})")
            else:
                logger.warning(f"[WARN] JobResult not found for job {job_id}, file: {filename}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to update JobResult: {filename} - {e}")
            db.session.rollback()
    
    def _update_progress(
        self,
        progress_store: Dict,
        job_id: int,
        stage: str,
        current: int,
        total: int,
        **kwargs
    ):
        """Update progress in the shared store."""
        message = self.PROGRESS_MESSAGES.get(stage, stage)
        
        # Format message with current/total and any additional kwargs
        format_vars = {'current': current, 'total': total}
        format_vars.update(kwargs)
        try:
            message = message.format(**format_vars)
        except KeyError:
            pass
        
        progress_percent = (current / total * 100) if total > 0 else 0
        
        progress_store[job_id] = {
            'status': 'completed' if stage == 'completed' else ('failed' if stage == 'failed' else 'processing'),
            'message': message,
            'progress': progress_percent,
            'total': total,
            'current': current
        }
        
        logger.debug(f"[PROGRESS] Job {job_id}: {stage} - {current}/{total} ({progress_percent:.1f}%)")
    
    def _generate_csv(
        self,
        job_id: int,
        results: List[Dict],
        username: str
    ) -> str:
        """Generate CSV file with results."""
        # Create results folder if not exists
        results_folder = self.config.get('RESULTS_FOLDER')
        os.makedirs(results_folder, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"{username}_{timestamp}.csv"
        csv_path = os.path.join(results_folder, csv_filename)
        
        # Sort results by filename for consistent ordering
        sorted_results = sorted(results, key=lambda x: x.get('filename', ''))
        
        # Write CSV
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['No', 'Filename', 'NIM', 'Nama', 'Skor', 'Status OCR Docling', 'Evaluasi'])
            
            # Data rows
            for idx, result in enumerate(sorted_results, 1):
                # Use clearer failsafe message for unreadable NIM/name
                nim = result.get('nim', '')
                if not nim or nim in ('TIDAK_DITEMUKAN', 'ERROR', ''):
                    nim = '[Tidak Terbaca]'
                
                student_name = result.get('student_name', '')
                if not student_name or student_name in ('TIDAK_DITEMUKAN', 'ERROR', ''):
                    student_name = '[Tidak Terbaca]'
                
                ocr_status = result.get('docling_ocr_status') or 'Tidak Diketahui'
                ocr_detail = result.get('docling_ocr_detail') or 'Status OCR tidak tersedia.'

                writer.writerow([
                    idx,
                    result.get('filename', ''),
                    nim,
                    student_name,
                    result.get('score', ''),
                    f"{ocr_status} - {ocr_detail}",
                    result.get('evaluation', '')
                ])
        
        logger.info(f"[CSV] CSV dibuat: {csv_path} ({len(sorted_results)} rows)")
        return csv_path
