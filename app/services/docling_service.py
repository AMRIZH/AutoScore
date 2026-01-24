"""
Docling PDF parsing service for AutoScoring application.
"""

import gc
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# Supported file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif', 
                    '.tiff', '.tif', '.svg', '.ico', '.raw', '.cr2', '.nef', '.arw'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx'}
TEXT_EXTENSIONS = {'.txt', '.md', '.markdown'}


class DoclingService:
    """Service for parsing PDFs, DOCX, and images using Docling with optional OCR support."""
    
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
            from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            
            # Configure pipeline options for PDF
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
            
            # Build format options for supported types
            format_options = {
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
            
            # Add image format support
            try:
                format_options[InputFormat.IMAGE] = ImageFormatOption()
                logger.info("Image format support diaktifkan")
            except Exception as e:
                logger.warning(f"Image format support tidak tersedia: {e}")
            
            # Create converter
            self._converter = DocumentConverter(format_options=format_options)
            self._initialized = True
            logger.info("Docling DocumentConverter berhasil diinisialisasi")
            
        except ImportError as e:
            logger.error(f"Gagal mengimpor Docling: {e}")
            raise RuntimeError(f"Docling tidak terinstall dengan benar: {e}")
        except Exception as e:
            logger.error(f"Gagal menginisialisasi Docling: {e}")
            raise RuntimeError(f"Gagal menginisialisasi Docling: {e}")
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type based on extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return 'pdf'
        elif ext in {'.doc', '.docx'}:
            return 'docx'
        elif ext in IMAGE_EXTENSIONS:
            return 'image'
        elif ext in TEXT_EXTENSIONS:
            return 'text'
        else:
            return 'unknown'
    
    def parse_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Parse a PDF file and extract text content.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text in markdown format (LLM-ready), or None if failed
        """
        return self.parse_document(pdf_path)
    
    def parse_document(self, file_path: str) -> Optional[str]:
        """
        Parse a document file (PDF, DOCX, or image) and extract text content.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text in markdown format (LLM-ready), or None if failed
        """
        return self._parse_document_safe(file_path)
    
    def _parse_document_safe(self, file_path: str) -> Optional[str]:
        """Safe wrapper that catches exceptions and returns None."""
        try:
            return self._parse_document_internal(file_path)
        except Exception as e:
            logger.error(f"Gagal memproses dokumen {file_path}: {e}")
            self._cleanup_memory()
            return None
    
    def _parse_document_internal(self, file_path: str) -> str:
        """
        Internal document parsing that raises exceptions on failure.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text in markdown format (LLM-ready)
            
        Raises:
            Exception: If parsing fails for any reason
        """
        file_type = self._get_file_type(file_path)
        logger.info(f"Memproses dokumen ({file_type}): {file_path}")
        
        # Plain text files can be read directly
        if file_type == 'text':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info(f"File teks berhasil dibaca: {file_path} ({len(content)} karakter)")
                return content
            except UnicodeDecodeError:
                # Try with latin-1 encoding as fallback
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                logger.info(f"File teks berhasil dibaca (latin-1): {file_path} ({len(content)} karakter)")
                return content
        
        # Initialize converter for non-text files
        self._initialize_converter()
        
        # Convert document
        result = self._converter.convert(file_path)
        
        # Export to markdown (LLM-ready format)
        markdown_text = result.document.export_to_markdown()
        
        logger.info(f"Dokumen berhasil diproses: {file_path} ({len(markdown_text)} karakter)")
        
        # Cleanup memory after processing
        self._cleanup_memory()
        
        return markdown_text
    
    def parse_image(self, image_path: str) -> Optional[str]:
        """
        Parse an image file using OCR and extract text content.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text in markdown format (LLM-ready), or None if failed
        """
        return self.parse_document(image_path)
    
    def parse_multiple_documents(self, file_paths: List[str]) -> Optional[str]:
        """
        Parse multiple document files and combine their content.
        
        Args:
            file_paths: List of paths to document files
            
        Returns:
            Combined extracted text in markdown format, or None if all failed
        """
        if not file_paths:
            return None
        
        combined_content = []
        
        for idx, file_path in enumerate(file_paths, 1):
            logger.info(f"Memproses dokumen {idx}/{len(file_paths)}: {os.path.basename(file_path)}")
            
            content = self.parse_document(file_path)
            if content:
                # Add file separator for multiple documents
                file_name = os.path.basename(file_path)
                combined_content.append(f"--- Dokumen: {file_name} ---\n{content}")
            else:
                logger.warning(f"Gagal memproses dokumen: {file_path}")
        
        if not combined_content:
            return None
        
        return "\n\n".join(combined_content)
    
    def parse_pdf_with_retry(self, pdf_path: str, max_retries: int = 3) -> Optional[str]:
        """
        Parse PDF with retry logic.
        
        Args:
            pdf_path: Path to the PDF file
            max_retries: Maximum number of retry attempts
            
        Returns:
            Extracted text or None if all retries failed
        """
        return self.parse_document_with_retry(pdf_path, max_retries)
    
    def parse_document_with_retry(self, file_path: str, max_retries: int = 3) -> Optional[str]:
        """
        Parse document with retry logic and exponential backoff.
        
        Args:
            file_path: Path to the document file
            max_retries: Maximum number of retry attempts
            
        Returns:
            Extracted text or None if all retries failed
        """
        import time
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Use internal method that raises exceptions
                result = self._parse_document_internal(file_path)
                return result
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Percobaan {attempt + 1}/{max_retries} gagal untuk {file_path}: {e}")
                self._cleanup_memory()
                
                # Exponential backoff: 1s, 2s, 4s...
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Menunggu {wait_time}s sebelum retry...")
                    time.sleep(wait_time)
        
        logger.error(f"Semua percobaan gagal untuk {file_path}. Error terakhir: {last_error}")
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
            'gpu_name': None,
            'supported_formats': list(DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS)
        }
        
        try:
            import torch
            status['gpu_available'] = torch.cuda.is_available()
            if status['gpu_available']:
                status['gpu_name'] = torch.cuda.get_device_name(0)
        except ImportError:
            pass
        
        return status
