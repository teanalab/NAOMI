from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings


def build_embeddings():
    """Build the embedding model used for retrieval."""
    return OllamaEmbeddings(model="nomic-embed-text")


def _safe_answer(doc):
    """
    Prefer metadata['answer'] if it exists; otherwise fall back to page_content.
    """
    if doc is None:
        return ""
    return doc.metadata.get("answer", doc.page_content)


def format_chat_history(chat_history, n=5):
    """
    Format the last n messages of chat history.
    Default n=5 because the paper describes retrieval over a 5-turn window.
    """
    last_n = chat_history[-n:]
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in last_n])


def get_mi_retrievers(embeddings):
    """
    Load the FAISS indexes used for NAOMI-RAG.
    """
    mi_k3_db = FAISS.load_local(
        "data/faiss_db/faiss_index_ob_k3",
        embeddings,
        allow_dangerous_deserialization=True,
    )
    mi_k5_db = FAISS.load_local(
        "data/faiss_db/faiss_index_ob_k5",
        embeddings,
        allow_dangerous_deserialization=True,
    )

    return [
        mi_k3_db.as_retriever(),
        mi_k5_db.as_retriever(),
    ]


def retrieve_results(query, retrievers, embedding_model, k=1):
    """
    Retrieve top-k results from each retriever using the same query embedding.
    """
    results = []
    query_vector = embedding_model.embed_query(query)

    for retriever in retrievers:
        hits = retriever.vectorstore.similarity_search_by_vector(query_vector, k=k)
        results.append(hits)

    return results


def format_context(results):
    """
    Format retrieved therapist examples for insertion into the generation prompt.
    """
    examples = []
    example_id = 1

    for hit_list in results:
        for doc in hit_list:
            text = _safe_answer(doc).strip()
            if text:
                examples.append(f"Example {example_id}:\n{text}")
                example_id += 1

    if not examples:
        return "(No retrieved motivational interviewing therapist examples found.)"

    return "\n\n".join(examples)


def format_retrieval(results):
    """
    Rendering of raw retrieval hits.
    """
    chunks = []
    example_id = 1

    for hit_list in results:
        for doc in hit_list:
            raw_text = doc.page_content.strip() if doc.page_content else ""
            if raw_text:
                chunks.append(f"Example {example_id}:\n{raw_text}")
                example_id += 1

    if not chunks:
        return "(No retrieval results found.)"

    return "\n\n".join(chunks)