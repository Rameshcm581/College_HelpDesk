# backend/Services/HelpdeskService/resources/pdfService.py
import io
import logging
import os
import pathlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Callable, List, Optional
import pypdf
from PIL import Image

from configs.base_config import BaseConfig
from resources.errors import FileValidationError, OCRExtractionError

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    char_count: int
    is_scanned: bool = False
    ocr_applied: bool = False
    ocr_error: Optional[str] = None


@dataclass
class DocumentChunkData:
    chunk_index: int
    page_number: int
    content: str
    token_count: int
    metadata: dict = field(default_factory=dict)


class PDFExtractionService:
    """Service for validating, safely storing, extracting text, detecting scanned pages,
    performing OCR, and generating structure-aware chunks from institutional PDFs.
    """

    def __init__(self, custom_ocr_engine: Optional[Callable[[Image.Image], str]] = None):
        self.custom_ocr_engine = custom_ocr_engine

    def validate_pdf_content(self, file_content: bytes, max_size_mb: Optional[int] = None) -> None:
        """Validates magic header, file size, and readable PDF structure.
        Raises FileValidationError on validation failure.
        """
        max_mb = max_size_mb or BaseConfig.MAX_UPLOAD_SIZE_MB
        max_bytes = max_mb * 1024 * 1024

        if not file_content or len(file_content) == 0:
            raise FileValidationError("Uploaded file is empty.", status_code=400)

        if len(file_content) > max_bytes:
            raise FileValidationError(
                f"File size exceeds institutional limit of {max_mb} MB.",
                status_code=413,
                details={"size_bytes": len(file_content), "max_bytes": max_bytes},
            )

        # Check PDF magic bytes (%PDF)
        if not file_content.startswith(b"%PDF"):
            raise FileValidationError(
                "Invalid file signature: uploaded file is not a valid PDF document.",
                status_code=400,
            )

        # Verify PDF structure can be read by pypdf
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_content))
            if len(reader.pages) == 0:
                raise FileValidationError("PDF document contains no pages.", status_code=400)
        except Exception as exc:
            raise FileValidationError(
                f"PDF structure is damaged or corrupt: {str(exc)}",
                status_code=400,
            )

    def generate_safe_storage_path(
        self,
        document_id: uuid.UUID,
        version_number: int,
        original_filename: str,
    ) -> pathlib.Path:
        """Generates a secure, non-executable storage path within STORAGE_PATH,
        disregarding untrusted user-supplied filenames to prevent path traversal.
        """
        base_dir = pathlib.Path(BaseConfig.STORAGE_PATH).resolve()
        target_dir = base_dir / "documents" / str(document_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate a collision-resistant safe filename
        safe_suffix = uuid.uuid4().hex[:12]
        safe_filename = f"v{version_number}_{safe_suffix}.pdf"
        target_file = target_dir / safe_filename

        return target_file

    def is_scanned_page(self, page: pypdf.PageObject, extracted_text: str) -> bool:
        """Detects whether a PDF page is a scanned document page based on
        low character density (< 40 chars) and embedded image presence.
        """
        cleaned = re.sub(r'\s+', '', extracted_text)
        has_images = False
        try:
            has_images = len(page.images) > 0
        except Exception:
            pass

        return len(cleaned) < 40 and has_images

    def perform_ocr_on_page(self, page: pypdf.PageObject) -> str:
        """Extracts text from images embedded in a scanned page using OCR."""
        # 1. Custom/Mock OCR engine takes precedence if configured
        if self.custom_ocr_engine is not None:
            combined = []
            for img_file in page.images:
                try:
                    img = Image.open(io.BytesIO(img_file.data))
                    ocr_res = self.custom_ocr_engine(img)
                    if ocr_res:
                        combined.append(ocr_res)
                except Exception as exc:
                    raise OCRExtractionError(f"Custom OCR engine failure: {str(exc)}")
            return "\n\n".join(combined).strip()

        # 2. Standard Tesseract/pytesseract if installed
        try:
            import pytesseract
            combined = []
            for img_file in page.images:
                img = Image.open(io.BytesIO(img_file.data))
                text = pytesseract.image_to_string(img)
                if text.strip():
                    combined.append(text.strip())
            return "\n\n".join(combined).strip()
        except ImportError:
            raise OCRExtractionError("pytesseract library is not installed.")
        except Exception as exc:
            # Handles pytesseract.TesseractNotFoundError or execution errors
            raise OCRExtractionError(f"Tesseract OCR execution error: {str(exc)}")

    def extract_pages(
        self,
        file_content: bytes,
        allow_ocr: bool = True,
        raise_on_ocr_failure: bool = False,
    ) -> List[ExtractedPage]:
        """Extracts text page-by-page preserving 1-based page numbers.
        Detects scanned pages and invokes OCR when appropriate.
        Handles extraction and OCR errors safely.
        """
        self.validate_pdf_content(file_content)

        reader = pypdf.PdfReader(io.BytesIO(file_content))
        extracted_pages: List[ExtractedPage] = []

        for idx, page in enumerate(reader.pages, start=1):
            text = ""
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                logger.warning("Error extracting text on page %d: %s", idx, exc)

            cleaned_text = re.sub(r'\n\s*\n', '\n\n', text).strip()
            is_scanned = self.is_scanned_page(page, cleaned_text)
            ocr_applied = False
            ocr_error = None

            if is_scanned and allow_ocr:
                try:
                    ocr_text = self.perform_ocr_on_page(page)
                    if ocr_text:
                        cleaned_text = ocr_text
                        ocr_applied = True
                except Exception as exc:
                    ocr_error = str(exc)
                    logger.warning("OCR processing failed for page %d: %s", idx, exc)
                    if raise_on_ocr_failure:
                        raise OCRExtractionError(f"Failed to process scanned page {idx}: {ocr_error}")

            extracted_pages.append(
                ExtractedPage(
                    page_number=idx,
                    text=cleaned_text,
                    char_count=len(cleaned_text),
                    is_scanned=is_scanned,
                    ocr_applied=ocr_applied,
                    ocr_error=ocr_error,
                )
            )

        return extracted_pages

    def chunk_document(
        self,
        pages: List[ExtractedPage],
        document_title: str,
        academic_year: str,
        department: str,
        version_id: Optional[uuid.UUID] = None,
        max_chunk_chars: int = 700,
        overlap_chars: int = 100,
    ) -> List[DocumentChunkData]:
        """Divides pages into structure-aware chunks with preserved page numbers and metadata."""
        chunks: List[DocumentChunkData] = []
        global_chunk_idx = 0

        for page in pages:
            page_text = page.text
            if not page_text:
                continue

            # Split page by paragraph breaks first
            paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
            current_chunk_parts = []
            current_length = 0

            for para in paragraphs:
                para_len = len(para)
                if current_length + para_len <= max_chunk_chars:
                    current_chunk_parts.append(para)
                    current_length += para_len + 2
                else:
                    if current_chunk_parts:
                        chunk_text = "\n\n".join(current_chunk_parts)
                        approx_tokens = max(1, len(chunk_text) // 4)
                        chunks.append(
                            DocumentChunkData(
                                chunk_index=global_chunk_idx,
                                page_number=page.page_number,
                                content=chunk_text,
                                token_count=approx_tokens,
                                metadata={
                                    "document_title": document_title,
                                    "academic_year": academic_year,
                                    "department": department,
                                    "page_number": page.page_number,
                                    "version_id": str(version_id) if version_id else None,
                                    "is_scanned": page.is_scanned,
                                },
                            )
                        )
                        global_chunk_idx += 1

                    current_chunk_parts = [para]
                    current_length = para_len

            if current_chunk_parts:
                chunk_text = "\n\n".join(current_chunk_parts)
                approx_tokens = max(1, len(chunk_text) // 4)
                chunks.append(
                    DocumentChunkData(
                        chunk_index=global_chunk_idx,
                        page_number=page.page_number,
                        content=chunk_text,
                        token_count=approx_tokens,
                        metadata={
                            "document_title": document_title,
                            "academic_year": academic_year,
                            "department": department,
                            "page_number": page.page_number,
                            "version_id": str(version_id) if version_id else None,
                            "is_scanned": page.is_scanned,
                        },
                    )
                )
                global_chunk_idx += 1

        return chunks


pdf_service = PDFExtractionService()
