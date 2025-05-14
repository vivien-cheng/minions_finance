from minions_finance.utils.retrievers import bm25_retrieve_top_k_chunks

def retrieve_relevant_context(query: str, context: str, k: int = 5) -> list[str]:
    """Retrieves relevant snippets from the context based on the query using BM25."""
    # Split context into paragraphs and wrap each in a dict with a 'text' key
    chunks = [{"text": chunk} for chunk in context.split("\n\n") if chunk.strip()]
    return bm25_retrieve_top_k_chunks(query=query, chunks=chunks, k=k)