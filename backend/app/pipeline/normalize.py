from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Callable, Iterable, List, Optional, Protocol
import unicodedata

from langchain_core.documents import Document

_WS = re.compile(r"[ \t\u00A0]+")
_MULTI_NL = re.compile(r"\n{3,}")
_DEHYPH = re.compile(r"(\w)-\n(\w)")

class DocumentNormalizer:
    def __init__(self):
        pass

    def _extract_filename(self, file_path: str) -> str:
        return Path(file_path).name
    
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        s = unicodedata.normalize("NFC", text)
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = _DEHYPH.sub(r"\1\2", s)
        s = _WS.sub(" ", s)
        s = _MULTI_NL.sub("\n\n", s)

        return s.strip()
    
    def normalize(
            self, 
            docs: Iterable[Document],
    ) -> List[Document]:
        """
        Normalize a list of documents.
        """
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        out: List[Document] = [] 

        for d in docs:
            meta = dict(d.metadata) if d.metadata else {}
            src = meta.get("source")
            file_name = self._extract_filename(src) if src else "unknown"
            ext = Path(src).suffix if src else ""

            content = self._clean_text(d.page_content)

            if not content:
                continue

            meta.update({
                "ingested_at": now,
                "ext": ext.lower(),
                "file_name": file_name,
            })

            out.append(Document(page_content=content, metadata=meta))

        print(f"Out : {[doc.metadata for doc in out]}")

        return out


