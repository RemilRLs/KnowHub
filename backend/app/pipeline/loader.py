import logging
import pdfplumber


from app.core.hash_utils import compute_sha256
from app.pipeline.pdf_table_extractor import extract_tables_from_pdf, get_table_bboxes

from pathlib import Path
from typing import List, Optional, Dict
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PDFPlumberLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
)

logger = logging.getLogger(__name__)

LOADER_MAPPING = {
    ".pdf": PDFPlumberLoader,
    ".docx": UnstructuredWordDocumentLoader,
    ".pptx": UnstructuredPowerPointLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
}



class DocumentLoader:
    def __init__(
        self,
        default_collection: str = "default",
        max_file_size_bytes: Optional[int] = 50 * 1024 * 1024,  # 50 MB
        extract_pdf_tables: bool = True, 
        table_extraction_flavor: str = "lattice", # Default mode to check for table borders
        min_table_accuracy: float = 80.0, # Minimum accuracy to accept a table extraction
    ):

        self.default_collection = default_collection
        self.max_file_size_bytes = max_file_size_bytes
        self.extract_pdf_tables = extract_pdf_tables
        self.table_extraction_flavor = table_extraction_flavor
        self.min_table_accuracy = min_table_accuracy

    def _validate_file(self, file_path: Path) -> str:
        """
        
        """

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        if self.max_file_size_bytes is not None and file_path.stat().st_size > self.max_file_size_bytes:
            raise ValueError(f"File too large: {file_path} exceeds {self.max_file_size_bytes} bytes")
        
        ext = file_path.suffix.lower()
        if ext not in LOADER_MAPPING:
            raise ValueError(f"Unsupported file type: {ext}")

        return ext
    
    def _load_one(self, file_path: Path) -> List[Document]:
        """Load a single file with the proper loader."""
        p = Path(file_path).resolve()
        ext = self._validate_file(p)
        
        # For PDFs, if table extraction is enabled, use the special loader
        if ext == ".pdf" and self.extract_pdf_tables:
            return self._load_pdf_with_table_exclusion(p)
        
        loader_cls = LOADER_MAPPING[ext]
        loader = loader_cls(str(p))
        docs = loader.load()

        if ext == ".pdf":
            for d in docs:
                d.metadata["page"] = d.metadata.get("page", 0) + 1
        
        return docs
    
    def _load_pdf_with_table_exclusion(self, file_path: Path) -> List[Document]:
        """
        We load a PDF while excluding table areas to avoid duplication with table extraction from Camelot.
        """
        # I get first the table bounding boxes from Camelot
        table_bboxes = get_table_bboxes(
            pdf_path=file_path,
            flavor=self.table_extraction_flavor,
            min_accuracy=self.min_table_accuracy,
        )
        
        docs = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Get the table bounding boxes for this page
                    page_table_bboxes = table_bboxes.get(page_num, [])
                    
                    if page_table_bboxes:
                        # Extract text outside of table areas
                        # So here I only extract text that is not in table areas
                        text = self._extract_text_excluding_tables(page, page_table_bboxes)
                    else:
                        # No tables, extract all text
                        text = page.extract_text() or ""
                    
                    if text.strip():
                        doc = Document(
                            page_content=text,
                            metadata={
                                "page": page_num,
                                "source": str(file_path),
                                "file_path": str(file_path),
                            }
                        )
                        docs.append(doc)
        
        except Exception as e:
            logger.error(f"Error loading PDF {file_path.name} with table exclusion: {e}")

            # Fallback on standard loader
            loader = PDFPlumberLoader(str(file_path))
            docs = loader.load()
            for d in docs:
                d.metadata["page"] = d.metadata.get("page", 0) + 1
        
        return docs
    
    def _extract_text_excluding_tables(self, page, table_bboxes: List[tuple]) -> str:
        """
        Extract text from a PDF page excluding specified table bounding boxes (by overlap).
        """
        page_h = page.height
        margin = 2 

        # Convert the bboxes Camelot -> pdfplumber coordinate system (top-left origin)
        excl_boxes = []
        for (x0, y0, x1, y1) in table_bboxes:
            # I invert coordinates because Camelot uses bottom-left origin and pdfplumber top-left
            top = max(0, page_h - y1 - margin)
            bottom = min(page_h, page_h - y0 + margin)
            excl_boxes.append((x0 - margin, top, x1 + margin, bottom))

        # Overlap function for rectangle-rectangle
        def overlaps(a, b) -> bool:
            ax0, at, ax1, ab = a  # a: (x0, top, x1, bottom)
            bx0, bt, bx1, bb = b
            # No overlap if separated horizontally or vertically
            if ax1 <= bx0 or bx1 <= ax0:
                return False
            if ab <= bt or bb <= at:
                return False
            return True

        # Extract words, excluding those that overlap with at least one table bbox
        words = page.extract_words(use_text_flow=True) or []
        keep = []
        for w in words:
            wbox = (w["x0"], w["top"], w["x1"], w["bottom"])
            if any(overlaps(wbox, tb) for tb in excl_boxes): # The word is inside a table area
                continue
            keep.append(w) # The word is outside table areas

        # Reconstruct text from kept words
        # Group by approximate line (key = rounded top)
        from collections import defaultdict
        lines = defaultdict(list)
        for w in keep:
            key = round(w["top"], 1)
            lines[key].append((w["x0"], w["text"]))

        # Sort by y then x, join texts
        ordered_lines = []
        for _, items in sorted(lines.items(), key=lambda kv: kv[0]):
            ordered_lines.append(" ".join(t for _, t in sorted(items, key=lambda it: it[0])))

        text = "\n".join(l for l in ordered_lines if l.strip())
        return text

    
    def _extract_pdf_tables(self, file_path: Path) -> List[Document]:
        """
        Extract tables from a PDF as separate documents.
        """
        try:
            tables = extract_tables_from_pdf(
                pdf_path=file_path,
                flavor=self.table_extraction_flavor,
                pages="all",
                min_accuracy=self.min_table_accuracy,
            )
            
            if tables:
                logger.info(f"Extracted {len(tables)} table(s) from {file_path.name}")
            
            return tables
            
        except ImportError:
            logger.warning(
                "Camelot not installed, table extraction disabled. "
                "Install with: pip install camelot-py[cv]"
            )
            return []
        except Exception as e:
            logger.error(f"Error extracting tables from {file_path.name}: {e}")
            return []

    def load_documents(self, file_paths: List[Path]) -> List[Document]:
        """
        Load documents from the given file paths.
        """

        all_docs: List[Document] = []

        for file_path in file_paths:
            try:
                p = Path(file_path)
                docs = self._load_one(p)
                if not isinstance(docs, list):
                    logger.warning("Loader for %s returned %r, coercing to []", p, type(docs))
                    docs = []

                logger.info("Loaded %d document(s) from %s", len(docs), p)
                
                table_docs = []
                if p.suffix.lower() == ".pdf" and self.extract_pdf_tables:
                    table_docs = self._extract_pdf_tables(p)
                    if table_docs:
                        logger.info(f"Extracted {len(table_docs)} table(s) from {p.name}")

                file_hash = compute_sha256(p)

                enriched_docs: List[Document] = []
                
                for d in docs:
                    meta = dict(d.metadata or {})
                    meta["file_sha256"] = file_hash
                    meta["content_type"] = meta.get("content_type", "text")
                    enriched_docs.append(Document(page_content=d.page_content, metadata=meta))
                
                for d in table_docs:
                    meta = dict(d.metadata or {})
                    meta["file_sha256"] = file_hash
                    enriched_docs.append(Document(page_content=d.page_content, metadata=meta))

                all_docs.extend(enriched_docs)

            except Exception as e:
                logger.exception("Error loading %s: %s", file_path, e)
                continue

        return all_docs