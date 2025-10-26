import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

from typing import List


class QwenEmbedder:
    """
    
    """
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-0.6B"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            padding_side="left",
            use_fast=True
        )
        
        self.model = AutoModel.from_pretrained(
            model_name,
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32, # GPU area float16 but CPU float32.
        ).to(self.device)
        
        self.model.eval()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


    @staticmethod

    def _last_token_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """
        Applies a pooling operation on the last hidden states of a sequence based on the attention mask.

        This method determines whether the input sequences are left-padded or not and selects the appropriate
        token from the last hidden states tensor. If the sequences are left-padded, the last token is selected.
        Otherwise, the token corresponding to the actual sequence length (excluding padding) is selected.

        https://huggingface.co/Qwen/Qwen3-Embedding-0.6B

        Args:
            last_hidden_states (torch.Tensor): A tensor of shape (batch_size, seq_length, hidden_size) 
            representing the last hidden states of the model.
            attention_mask (torch.Tensor): A tensor of shape (batch_size, seq_length) representing the 
            attention mask, where 1 indicates valid tokens and 0 indicates padding.

        Returns:
            torch.Tensor: A tensor of shape (batch_size, hidden_size) representing the pooled token embeddings 
            for each sequence in the batch.
        """
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            seq_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), seq_lengths]

    def embed(self, texts: List[str], max_length: int = 1024) -> List[List[float]]:
        """
        Generates embeddings for a list of texts with memory optimizations.
        """
        with torch.inference_mode():
            # We translate texts first to tokens
            inputs = self.tokenizer(
                texts,
                padding=True,  # To add padding to the shortest sequence in the batch
                truncation=True,  # To cut off texts longer than max_length
                max_length=max_length,
                return_tensors="pt"
            ).to(self.device)

            outputs = self.model(**inputs)
            embeddings = self._last_token_pool(outputs.last_hidden_state, inputs["attention_mask"]) # We get the embeddings of the last token
            embeddings = F.normalize(embeddings, p=2, dim=1)  # Normalize the embeddings to unit length (L2 norm)

            return embeddings.cpu().float() 
    
if __name__ == "__main__":
    embedder = QwenEmbedder()

    texts = [
        "The capital of China is Beijing.",
        "Gravity pulls objects toward each other.",
        "Paris is the capital of France."
    ]

    embeddings = embedder.embed(texts)
    print(f"Shape des embeddings : {embeddings.shape}") 

    norms = torch.norm(embeddings, dim=1)
    print(f"Normes des vecteurs : {norms}")

    sim = embeddings @ embeddings.T
    print("Matrice de similarité cosinus :")
    print(sim)