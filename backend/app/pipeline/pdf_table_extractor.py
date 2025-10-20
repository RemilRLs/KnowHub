import logging
import camelot
import pandas as pd 

from pathlib import Path

from typing import List, Optional, Dict, Any

from langchain_core.documents import Document


logger = logging.getLogger(__name__)


class PDFTableExtractor:
    """
    """
    
    def __init__(
        self,
        flavor: str = "lattice",  
        table_areas: Optional[List[str]] = None,
        columns: Optional[List[str]] = None,
    ):
        """

        """
        if flavor not in ("lattice", "stream"):
            raise ValueError(f"flavor doit être 'lattice' ou 'stream', reçu: {flavor}")
            
        self.flavor = flavor
        self.table_areas = table_areas
        self.columns = columns
        
    def extract_tables(
        self,
        pdf_path: Path,
        pages: str = "all",
        min_accuracy: float = 80.0,
    ) -> List[Document]:
        """    
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF was not found: {pdf_path}")
            
        logger.info(f"Extraction of tables from {pdf_path.name} (flavor={self.flavor}, pages={pages})")
        
        try:
            kwargs = {
                "flavor": self.flavor,
                "pages": pages,
            }
            
            if self.table_areas:
                kwargs["table_areas"] = self.table_areas
            if self.columns:
                kwargs["columns"] = self.columns
                
            tables = camelot.read_pdf(str(pdf_path), **kwargs)
            
            logger.info(f"Found {len(tables)} table(s) in {pdf_path.name}")
            
            documents = []
            for idx, table in enumerate(tables):
                accuracy = table.parsing_report.get("accuracy", 0.0)
                if accuracy < min_accuracy:
                    logger.warning(
                        f"Table {idx+1} on page {table.page} ignored "
                        f"(accuracy={accuracy:.1f}% < {min_accuracy}%)"
                    )
                    continue
                
                # Expect the accuracy to be sufficient here (more than min_accuracy)
                doc = self._table_to_document(
                    table=table,
                    table_index=idx,
                    pdf_path=pdf_path,
                )
                documents.append(doc)

            logger.info(f"Extracted {len(documents)} valid table(s) from {pdf_path.name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error extracting tables from {pdf_path.name}: {e}")
            return []
    
    def _table_to_document(
        self,
        table: Any,
        table_index: int,
        pdf_path: Path,
    ) -> Document:
        """
        """
        df = table.df
        
        content = self._format_table_as_text(df, table)
        
        metadata = {
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "page": table.page,
            "table_index": table_index + 1,
            "table_accuracy": round(table.parsing_report.get("accuracy", 0.0), 2),
            "table_rows": len(df),
            "table_cols": len(df.columns),
            "extraction_method": self.flavor,
            "content_type": "table",
            "ext": pdf_path.suffix.lower(),
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _format_table_as_text(self, df, table: Any) -> str:
        """
        """
        content = ""
        try:
            content += df.to_markdown(index=False)
        except ImportError:
            logger.warning("tabulate not installed, using CSV format for table representation.")
            content += df.to_csv(index=False)
        except Exception as e:
            logger.error(f"Error formatting table: {e}")
            content += df.to_string(index=False)

        return content


def get_table_bboxes(
    pdf_path: Path,
    flavor: str = "lattice",
    pages: str = "all",
    min_accuracy: float = 80.0,
) -> Dict[int, List[tuple]]:
    """
    Extract table bounding boxes from a PDF using Camelot.
    """
    if not pdf_path.exists():
        logger.warning(f"PDF not found: {pdf_path}")
        return {}
    
    try:
        kwargs = {
            "flavor": flavor,
            "pages": pages,
        }
        
        tables = camelot.read_pdf(str(pdf_path), **kwargs)
        
        bboxes_by_page = {}
        for table in tables:
            accuracy = table.parsing_report.get("accuracy", 0.0)
            if accuracy < min_accuracy:
                continue
            
            page_num = table.page
            if page_num not in bboxes_by_page:
                bboxes_by_page[page_num] = []
            
            # Thanks to camelot's Table object for bbox attribute
            bbox = table._bbox
            bboxes_by_page[page_num].append(bbox)
        
        logger.info(f"Found table bounding boxes in {pdf_path.name}: {bboxes_by_page}")
        return bboxes_by_page
        
    except Exception as e:
        logger.error(f"Error extracting table bounding boxes from {pdf_path.name}: {e}")
        return {}


def extract_tables_from_pdf(
    pdf_path: Path,
    flavor: str = "lattice",
    pages: str = "all",
    min_accuracy: float = 80.0,
) -> tuple[List[Document], Dict[int, List[tuple]]]:
    """
    Extract tables and their bounding boxes from a PDF in a single pass.
    Returns (table_documents, bboxes_by_page)
    """
    extractor = PDFTableExtractor(flavor=flavor)
    
    if not pdf_path.exists():
        logger.warning(f"PDF not found: {pdf_path}")
        return [], {}
    
    try:
        kwargs = {
            "flavor": flavor,
            "pages": pages,
        }
        
        tables = camelot.read_pdf(str(pdf_path), **kwargs)
        logger.info(f"Found {len(tables)} table(s) in {pdf_path.name}")
        
        documents = []
        bboxes_by_page = {}
        
        for idx, table in enumerate(tables):
            accuracy = table.parsing_report.get("accuracy", 0.0)
            if accuracy < min_accuracy:
                logger.warning(
                    f"Table {idx+1} on page {table.page} ignored "
                    f"(accuracy={accuracy:.1f}% < {min_accuracy}%)"
                )
                continue
            
            # Extract table document
            doc = extractor._table_to_document(
                table=table,
                table_index=idx,
                pdf_path=pdf_path,
            )
            documents.append(doc)
            
            # Extract bounding box
            page_num = table.page
            if page_num not in bboxes_by_page:
                bboxes_by_page[page_num] = []
            bbox = table._bbox
            bboxes_by_page[page_num].append(bbox)
        
        logger.info(f"Extracted {len(documents)} valid table(s) from {pdf_path.name}")
        return documents, bboxes_by_page
        
    except Exception as e:
        logger.error(f"Error extracting tables from {pdf_path.name}: {e}")
        return [], {}

if __name__ == "__main__":
    # Test avec un PDF contenant une table
    # Remplacez par le chemin de votre PDF
    pdf_path = Path(r"E:\\tableaux_test.pdf")
    
    if pdf_path.exists():
        print(f"Test d'extraction de tables depuis: {pdf_path}")
        print("=" * 60)
        
        print("\n1. Test avec flavor='lattice' (flavor='lattice')")
        print("-" * 60)
        extractor_lattice = PDFTableExtractor(flavor="lattice")
        docs_lattice = extractor_lattice.extract_tables(pdf_path, min_accuracy=70.0)
        
        for i, doc in enumerate(docs_lattice):
            print(f"\nTable {i+1}:")
            print(f"  Page: {doc.metadata['page']}")
            print(f"  Précision: {doc.metadata['table_accuracy']}%")
            print(f"  Dimensions: {doc.metadata['table_rows']} lignes x {doc.metadata['table_cols']} colonnes")
            print(f"\nContenu:\n{doc.page_content}\n")
        
        # Tester avec flavor 'stream' (pour les tables sans bordures)
        print("\n2. Test avec flavor='stream' (flavor='stream')")
        print("-" * 60)
        extractor_stream = PDFTableExtractor(flavor="stream")
        docs_stream = extractor_stream.extract_tables(pdf_path, min_accuracy=70.0)
        
        for i, doc in enumerate(docs_stream):
            print(f"\nTable {i+1}:")
            print(f"  Page: {doc.metadata['page']}")
            print(f"  Précision: {doc.metadata['table_accuracy']}%")
            print(f"  Dimensions: {doc.metadata['table_rows']} lignes x {doc.metadata['table_cols']} colonnes")
            print(f"\nContenu:\n{doc.page_content}\n")
        
        print("=" * 60)
        print(f"Total: {len(docs_lattice)} table(s) avec 'lattice', {len(docs_stream)} table(s) avec 'stream'")
    else:
        print(f"ERREUR: Le fichier {pdf_path} n'existe pas!")
        print("\nUtilisation:")
        print("  1. Placez un PDF avec des tables dans le dossier")
        print("  2. Modifiez la variable 'pdf_path' avec le bon chemin")
        print("  3. Lancez: python -m app.pipeline.pdf_table_extractor")