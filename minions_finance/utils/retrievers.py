import torch
from typing import List, Dict, Any
from rank_bm25 import BM25Plus, BM25Okapi
from abc import ABC, abstractmethod
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
    print("SentenceTransformer not installed")

try:
    import faiss
except ImportError:
    faiss = None
    print("faiss not installed")


def bm25_retrieve_top_k_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    k: int = 3,
    text_key: str = "text"
) -> List[Dict[str, Any]]:
    """Retrieve top k most relevant chunks using BM25.
    
    Args:
        query: The search query
        chunks: List of dictionaries containing text chunks and metadata
        k: Number of top chunks to retrieve
        text_key: Key in the chunk dictionary containing the text
        
    Returns:
        List of top k most relevant chunks with their metadata
    """
    # Extract texts and create BM25 index
    texts = [chunk[text_key] for chunk in chunks]
    tokenized_texts = [text.split() for text in texts]
    bm25 = BM25Okapi(tokenized_texts)
    
    # Get scores for the query
    tokenized_query = query.split()
    scores = bm25.get_scores(tokenized_query)
    
    # Get indices of top k chunks
    top_k_indices = np.argsort(scores)[-k:][::-1]
    
    # Return top k chunks with their metadata
    return [chunks[i] for i in top_k_indices]


def combine_chunks(chunks: List[Dict[str, Any]], text_key: str = "text") -> str:
    """Combine multiple chunks into a single text.
    
    Args:
        chunks: List of dictionaries containing text chunks and metadata
        text_key: Key in the chunk dictionary containing the text
        
    Returns:
        Combined text
    """
    return "\n\n".join(chunk[text_key] for chunk in chunks)


def retrieve_and_combine(
    query: str,
    chunks: List[Dict[str, Any]],
    k: int = 3,
    text_key: str = "text"
) -> str:
    """Retrieve top k most relevant chunks and combine them.
    
    Args:
        query: The search query
        chunks: List of dictionaries containing text chunks and metadata
        k: Number of top chunks to retrieve
        text_key: Key in the chunk dictionary containing the text
        
    Returns:
        Combined text from top k most relevant chunks
    """
    top_chunks = bm25_retrieve_top_k_chunks(query, chunks, k, text_key)
    return combine_chunks(top_chunks, text_key)


class BaseEmbeddingModel(ABC):
    """
    Abstract base class defining interface for embedding models.
    """

    @abstractmethod
    def get_model(self, **kwargs):
        """Get or initialize the embedding model."""
        pass

    @abstractmethod
    def encode(self, texts, **kwargs) -> np.ndarray:
        """Encode texts to create embeddings."""
        pass


class EmbeddingModel(BaseEmbeddingModel):
    """
    Singleton implementation of embedding model using SentenceTransformer.
    """

    _instance = None
    _model = None
    _default_model_name = "intfloat/multilingual-e5-large-instruct"

    def __new__(cls, model_name=None):
        if cls._instance is None:
            cls._instance = super(EmbeddingModel, cls).__new__(cls)
            model_name = model_name or cls._default_model_name
            cls._model = SentenceTransformer(model_name)
            if torch.cuda.is_available():
                cls._model = cls._model.to(torch.device("cuda"))
        return cls._instance

    @classmethod
    def get_model(cls, model_name=None):
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._model

    @classmethod
    def encode(cls, texts, model_name=None) -> np.ndarray:
        model = cls.get_model(model_name)
        return model.encode(texts).astype("float32")


def embedding_retrieve_top_k_chunks(
    queries: List[str],
    chunks: List[str] = None,
    k: int = 10,
    embedding_model: BaseEmbeddingModel = None,
) -> List[str]:
    """
    Retrieves top k chunks using dense vector embeddings and FAISS similarity search

    Args:
        queries: List of query strings
        chunks: List of text chunks to search through
        k: Number of top chunks to retrieve
        embedding_model: Optional embedding model to use (defaults to EmbeddingModel)

    Returns:
        List of top k relevant chunks
    """

    # Use the provided embedding model or default to EmbeddingModel
    model = embedding_model or EmbeddingModel

    chunk_embeddings = model.encode(chunks).astype("float32")

    embedding_dim = chunk_embeddings.shape[1]
    index = faiss.IndexFlatIP(embedding_dim)
    index.add(chunk_embeddings)

    aggregated_scores = np.zeros(len(chunks))

    for query in queries:
        query_embedding = model.encode([query]).astype("float32")
        cur_scores, cur_indices = index.search(query_embedding, k)
        np.add.at(aggregated_scores, cur_indices[0], cur_scores[0])

    top_k_indices = np.argsort(aggregated_scores)[::-1][:k]

    relevant_chunks = [chunks[i] for i in top_k_indices]

    return relevant_chunks