"""
Docling PDF parsing service for AutoScoring application.
"""

import gc
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DoclingService:
    """Service for parsing PDFs using Docling with optional OCR support."""
    
    def __init__(self, enable_ocr: bool = True, use_gpu: bool = True):
        """
        Initialize Docling service.
        
        Args:
            enable_ocr: Whether to enable OCR for scanned documents
            use_gpu: Whether to use GPU acceleration if available
        """
        self.enable_ocr = enable_ocr
        self.use_gpu = use_gpu
        self._converter = None
        self._initialized = False
    
    def _initialize_converter(self):
        """Lazy initialization of DocumentConverter."""
        if self._initialized:
            return
        
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            
            # Configure pipeline options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self.enable_ocr
            
            # Configure OCR if enabled
            if self.enable_ocr:
                try:
                    from docling.datamodel.pipeline_options import EasyOcrOptions
                    pipeline_options.ocr_options = EasyOcrOptions(lang=['id', 'en'])
                    logger.info("EasyOCR diaktifkan dengan bahasa: Indonesia, English")
                except ImportError:
                    logger.warning("EasyOCR tidak tersedia, melanjutkan tanpa OCR")
                    pipeline_options.do_ocr = False
            
            # Configure GPU acceleration
            if self.use_gpu:
                try:
                    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
                    
                    # Check if CUDA is available
                    import torch
                    if torch.cuda.is_available():
                        accelerator_options = AcceleratorOptions(
                            device=AcceleratorDevice.CUDA
                        )
                        pipeline_options.accelerator_options = accelerator_options
                        logger.info(f"GPU acceleration diaktifkan: {torch.cuda.get_device_name(0)}")
                    else:
                        logger.info("GPU tidak tersedia, menggunakan CPU")
                except ImportError:
                    logger.info("PyTorch tidak tersedia, menggunakan CPU")
            
            # Create converter
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            self._initialized = True
            logger.info("Docling DocumentConverter berhasil diinisialisasi")
            
        except ImportError as e:
            logger.error(f"Gagal mengimpor Docling: {e}")
            raise RuntimeError(f"Docling tidak terinstall dengan benar: {e}")
        except Exception as e:
            logger.error(f"Gagal menginisialisasi Docling: {e}")
            raise RuntimeError(f"Gagal menginisialisasi Docling: {e}")
    
    def parse_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Parse a PDF file and extract text content.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text in markdown format (LLM-ready), or None if failed
        """
        try:
            # Initialize converter if needed
            self._initialize_converter()
            
            logger.info(f"Memproses PDF: {pdf_path}")
            
            # Convert PDF
            result = self._converter.convert(pdf_path)
            
            # Export to markdown (LLM-ready format)
            markdown_text = result.document.export_to_markdown()
            
            logger.info(f"PDF berhasil diproses: {pdf_path} ({len(markdown_text)} karakter)")
            
            # Cleanup memory after processing
            self._cleanup_memory()
            
            return markdown_text
            
        except Exception as e:
            logger.error(f"Gagal memproses PDF {pdf_path}: {e}")
            self._cleanup_memory()
            return None
    
    def parse_pdf_with_retry(self, pdf_path: str, max_retries: int = 3) -> Optional[str]:
        """
        Parse PDF with retry logic.
        
        Args:
            pdf_path: Path to the PDF file
            max_retries: Maximum number of retry attempts
            
        Returns:
            Extracted text or None if all retries failed
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = self.parse_pdf(pdf_path)
                if result is not None:
                    return result
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Percobaan {attempt + 1}/{max_retries} gagal untuk {pdf_path}: {e}")
                self._cleanup_memory()
        
        logger.error(f"Semua percobaan gagal untuk {pdf_path}. Error terakhir: {last_error}")
        return None
    
    def _cleanup_memory(self):
        """Clean up memory after processing."""
        gc.collect()
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.debug("GPU cache dibersihkan")
        except ImportError:
            pass
    
    def get_status(self) -> dict:
        """Get service status information."""
        status = {
            'initialized': self._initialized,
            'ocr_enabled': self.enable_ocr,
            'gpu_enabled': self.use_gpu,
            'gpu_available': False,
            'gpu_name': None
        }
        
        try:
            import torch
            status['gpu_available'] = torch.cuda.is_available()
            if status['gpu_available']:
                status['gpu_name'] = torch.cuda.get_device_name(0)
        except ImportError:
            pass
        
        return status
