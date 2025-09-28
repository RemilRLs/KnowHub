from typing import List, Iterable, Callable
from transformers import AutoTokenizer
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid



class DocumentSplitter:
    def __init__(
                 self,
                 chunk_chars: int = 1024,
                 chunk_overlap: int = 100,
                 hard_cap_chars: int = 1200,
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

    def split(self, docs: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks.
        """

        out: List[Document] = []

        for d in docs:
            chunks: List[Document] = self.splitter.split_documents([d])
            for i, c in enumerate(chunks):
                text = c.page_content or ""
                if len(text) < self.min_chunk_chars or len(text) > self.hard_cap_chars:
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