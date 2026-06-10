import os

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load GEMINI_API_KEY and optional settings from a .env file.
load_dotenv()


# These values must match ingest.py so both files use the same database.
CHROMA_FOLDER = "chroma_db"
COLLECTION_NAME = "skygrid_documents"
EMBEDDING_MODEL = "gemini-embedding-001"


def create_gemini_client():
    """Create a Gemini client for query embeddings."""
    # Read the Gemini API key from the environment or .env file.
    api_key = os.getenv("GEMINI_API_KEY")

    # Stop with a clear beginner-friendly error if the key is missing.
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Create and return the Gemini client.
    return genai.Client(api_key=api_key)


def embed_query(question):
    """Create a Gemini embedding for the user's question."""
    # Create the Gemini client that will call the embedding model.
    client = create_gemini_client()

    # Let users override the embedding model, while keeping a simple default.
    model_name = os.getenv("GEMINI_EMBEDDING_MODEL", EMBEDDING_MODEL)

    # Ask Gemini to convert the question into a search vector.
    response = client.models.embed_content(
        model=model_name,
        contents=question,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )

    # ChromaDB expects one plain embedding vector for this query.
    return response.embeddings[0].values


def get_collection():
    """Open the local ChromaDB collection."""
    # Connect to the local ChromaDB folder created by ingest.py.
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)

    # Load the existing collection from disk.
    collection = client.get_collection(name=COLLECTION_NAME)

    return collection


def retrieve_relevant_chunks(question, number_of_chunks=4):
    """Find the most relevant document chunks for a user question."""
    collection = get_collection()

    # Create a Gemini embedding for the user's question.
    question_embedding = embed_query(question)

    # Ask ChromaDB for the closest chunks to the question embedding.
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=number_of_chunks,
    )

    retrieved_chunks = []

    # Chroma returns lists inside lists because it supports multiple queries at once.
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    # Combine each chunk with its source file.
    for document, metadata in zip(documents, metadatas):
        retrieved_chunks.append(
            {
                "text": document,
                "source": metadata.get("source", "unknown"),
            }
        )

    return retrieved_chunks
