"""
Scoring service for AutoScoring application.
Orchestrates PDF parsing, LLM scoring, and CSV generation.
"""

import os
import csv
import logging
import threading
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from queue import Queue

from app.extensions import db
from app.models import Job, JobResult, SystemLog

logger = logging.getLogger(__name__)


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
        self._gemini_service = None
        
        # Queue for database updates (thread-safe)
        self._db_update_queue = Queue()
    
    @property
    def docling_service(self):
        """Lazy initialization of Docling service."""
        if self._docling_service is None:
            from app.services.docling_service import DoclingService
            self._docling_service = DoclingService(
                enable_ocr=self.config.get('ENABLE_OCR', True),
                use_gpu=True  # Auto-detect
            )
        return self._docling_service
    
    @property
    def gemini_service(self):
        """Lazy initialization of Gemini service."""
        if self._gemini_service is None:
            from app.services.gemini_service import GeminiService
            api_keys = self.config.get('GEMINI_API_KEYS', [])
            if not api_keys:
                raise RuntimeError("Tidak ada API key Gemini yang dikonfigurasi")
            self._gemini_service = GeminiService(
                api_keys=api_keys,
                max_retries=self.max_retries
            )
        return self._gemini_service
    
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
                job = Job.query.get(job_id)
                if not job:
                    logger.error(f"[ERROR] Job {job_id} tidak ditemukan di database")
                    return
                
                total_files = len(saved_files)
                logger.info(f"[INFO] Job {job_id}: Memproses {total_files} file PDF")
                logger.info(f"[INFO] Folder: {job_folder}")
                
                # Update job status
                job.status = 'processing'
                job.started_at = datetime.utcnow()
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
                job.completed_at = datetime.utcnow()
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
                    job = Job.query.get(job_id)
                    if job:
                        job.status = 'failed'
                        job.status_message = error_msg
                        job.completed_at = datetime.utcnow()
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
        score_min: int,
        score_max: int,
        enable_evaluation: bool
    ) -> Dict[str, Any]:
        """
        Process a single student file.
        
        Note: This runs in a worker thread, so NO database operations here!
        Return results to be processed in main thread.
        """
        filename = file_info['original_name']
        filepath = file_info['path']
        thread_name = threading.current_thread().name
        
        start_time = time.time()
        logger.debug(f"[{thread_name}] [FILE] Memproses: {filename}")
        
        # Step 1: Parse PDF with retry
        parse_start = time.time()
        logger.debug(f"[{thread_name}] [PARSE] Parsing PDF: {filename}")
        
        student_content = self.docling_service.parse_pdf_with_retry(
            filepath,
            max_retries=self.max_retries
        )
        
        parse_time = time.time() - parse_start
        
        if not student_content:
            error_msg = f'Gagal membaca file PDF setelah {self.max_retries} percobaan'
            logger.error(f"[{thread_name}] [FAIL] {filename}: {error_msg} ({parse_time:.2f}s)")
            
            return {
                'nim': 'ERROR',
                'student_name': 'ERROR',
                'score': None,
                'evaluation': error_msg,
                'error': True,
                'parse_time': parse_time,
                'score_time': 0
            }
        
        content_length = len(student_content)
        logger.debug(f"[{thread_name}] [OK] PDF parsed: {filename} ({content_length} chars, {parse_time:.2f}s)")
        
        # Step 2: Score with LLM
        score_start = time.time()
        logger.debug(f"[{thread_name}] [LLM] Menilai dengan LLM: {filename}")
        
        result = self.gemini_service.score_report(
            student_content=student_content,
            answer_key_content=answer_key_content,
            score_min=score_min,
            score_max=score_max,
            enable_evaluation=enable_evaluation
        )
        
        score_time = time.time() - score_start
        total_time = time.time() - start_time
        
        result['parse_time'] = parse_time
        result['score_time'] = score_time
        result['total_time'] = total_time
        result['content_length'] = content_length
        
        if result.get('error'):
            logger.debug(f"[{thread_name}] [FAIL] LLM scoring failed: {filename} ({score_time:.2f}s)")
        else:
            logger.debug(f"[{thread_name}] [OK] LLM scoring done: {filename} - Score: {result.get('score')} ({score_time:.2f}s)")
        
        logger.debug(f"[{thread_name}] [TIME] Total: {filename} dalam {total_time:.2f}s (parse: {parse_time:.2f}s, score: {score_time:.2f}s)")
        
        return result
    
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
                job_result.processed_at = datetime.utcnow()
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
            writer.writerow(['No', 'Filename', 'NIM', 'Nama', 'Skor', 'Evaluasi'])
            
            # Data rows
            for idx, result in enumerate(sorted_results, 1):
                writer.writerow([
                    idx,
                    result.get('filename', ''),
                    result.get('nim', 'TIDAK_DITEMUKAN'),
                    result.get('student_name', 'TIDAK_DITEMUKAN'),
                    result.get('score', ''),
                    result.get('evaluation', '')
                ])
        
        logger.info(f"[CSV] CSV dibuat: {csv_path} ({len(sorted_results)} rows)")
        return csv_path
