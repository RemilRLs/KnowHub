from typing import List, Iterable, Callable
from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
    MarkdownTextSplitter,
)
import uuid



class DocumentSplitter:
    def __init__(
                 self,
                 chunk_chars: int = 1024,
                 chunk_overlap: int = 100,
                 hard_cap_chars: int = 5000,
                 min_chunk_chars: int = 50,
                 ):
        self.chunk_chars = chunk_chars
        self.chunk_overlap = chunk_overlap
        self.hard_cap_chars = hard_cap_chars
        self.min_chunk_chars = min_chunk_chars

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_chars,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=False,
        )

        # Markdown
        self.md_headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]

        self.md_header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.md_headers_to_split_on
        )  

    def _emit_chunk(self, text: str, base_meta: dict, index) -> Document:
        meta = dict(base_meta or {})
        meta.update({
            "chunk_id": str(uuid.uuid4()),
            "chunk_index": index,
            "splitter_version": "md-header-v1",
            "chunk_chars": len(text),
        })
        return Document(page_content=text, metadata=meta)

    def _split_markdown(self, d: Document) -> List[Document]:
        """
        
        """

        out: List[Document] = []
        sections: List[Document] = self.md_header_splitter.split_text(d.page_content or "")

        for i, sec in enumerate(sections):
            txt = sec.page_content or ""
            if len(txt) < self.min_chunk_chars:
                continue

            if len(txt) <= self.chunk_chars:
                out.append(self._emit_chunk(txt, {**d.metadata, **sec.metadata}, i))
                continue


            # Too long, split further.

            base_meta = {**(d.metadata or {}), **(sec.metadata or {})}
            subchunks: List[Document] = self.splitter.split_documents([
                Document(page_content=txt, metadata=base_meta)
            ])

            for j, c in enumerate(subchunks):
                t = c.page_content or ""
                if len(t) < self.min_chunk_chars:
                    continue
                out.append(self._emit_chunk(t, c.metadata, f"{i}-{j}",))

        return out

    def split(self, docs: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks.
        """

        out: List[Document] = []

        for d in docs:

            # PPTX splitter (1 slide = 1 chunk)
            meta = dict(d.metadata or {})
            ext = meta.get("ext", "").lower()
            content_type = meta.get("content_type", "text")
            
            # Don't split tables, they are already optimized
            if content_type == "table":
                text = d.page_content or ""
                if len(text) >= self.min_chunk_chars:
                    meta.update({
                        "chunk_id": str(uuid.uuid4()),
                        "chunk_index": 0,
                        "splitter_version": "table-v1",
                        "chunk_chars": len(text),
                    })
                    out.append(Document(page_content=text, metadata=meta))
                continue

            if ext == ".pptx":
                text = d.page_content or ""
                if len(text) >= self.min_chunk_chars:
                    meta.update({
                        "chunk_id": str(uuid.uuid4()),
                        "chunk_index": 0,
                        "splitter_version": "pptx-v1",
                        "chunk_chars": len(text),
                    })
                    out.append(Document(page_content=text, metadata=meta))
                continue
            
            if ext == ".md":
                out.extend(self._split_markdown(d))
                for c in out:
                    print(f"MD Chunk: {c.metadata} / {c.page_content[:30]}...")
                continue

            # Generic splitter

            chunks: List[Document] = self.splitter.split_documents([d])
            for i, c in enumerate(chunks):
                text = c.page_content or ""
                if len(text) < self.min_chunk_chars: # Skip chunks that are too small (doesn't give much context).
                    continue
                
                meta = dict(c.metadata or {})
                meta.update({
                    "chunk_id": str(uuid.uuid4()),
                    "chunk_index": i,
                    "splitter_version": "char-v1",
                    "chunk_chars": len(text),
                })
                out.append(Document(page_content=text, metadata=meta))

        return out