import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load GEMINI_API_KEY and optional settings from a .env file.
load_dotenv()


# Project folders are kept as simple constants so beginners can find and change them.
DOCUMENTS_FOLDER = Path("documents")
CHROMA_FOLDER = Path("chroma_db")
COLLECTION_NAME = "skygrid_documents"

# Gemini turns text into embeddings that ChromaDB can store and search.
EMBEDDING_MODEL = "gemini-embedding-001"


def load_documents():
    """Load every .txt and .md file from the documents folder."""
    documents = []

    # Create the folder if it does not exist, so users know where to put files.
    DOCUMENTS_FOLDER.mkdir(exist_ok=True)

    # rglob searches inside subfolders too, which keeps the project flexible.
    for file_path in DOCUMENTS_FOLDER.rglob("*"):
        # Skip anything that is not a plain text or Markdown file.
        if file_path.suffix.lower() not in [".txt", ".md"]:
            continue

        # Read the document as UTF-8 text.
        text = file_path.read_text(encoding="utf-8")

        # Store both the text and the file name for later citations.
        documents.append({"source": str(file_path), "text": text})

    return documents


def split_text(text, chunk_size=800, overlap=150):
    """Split long text into smaller overlapping chunks."""
    chunks = []
    start = 0

    # Keep slicing until the whole document has been processed.
    while start < len(text):
        # The end position is chunk_size characters after the start.
        end = start + chunk_size

        # Save the current chunk after removing extra whitespace.
        chunk = text[start:end].strip()

        # Avoid storing empty chunks.
        if chunk:
            chunks.append(chunk)

        # Move forward, but keep some overlap so context is not cut too sharply.
        start += chunk_size - overlap

    return chunks


def create_gemini_client():
    """Create a Gemini client for making embeddings."""
    # Read the Gemini API key from the environment or .env file.
    api_key = os.getenv("GEMINI_API_KEY")

    # Stop with a clear beginner-friendly error if the key is missing.
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Create and return the Gemini client.
    return genai.Client(api_key=api_key)


def embed_texts(texts):
    """Create Gemini embeddings for a list of document chunks."""
    # Create the Gemini client that will call the embedding model.
    client = create_gemini_client()

    # Let users override the embedding model, while keeping a simple default.
    model_name = os.getenv("GEMINI_EMBEDDING_MODEL", EMBEDDING_MODEL)

    # Ask Gemini to convert the document chunks into vectors.
    response = client.models.embed_content(
        model=model_name,
        contents=texts,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )

    # ChromaDB expects a plain list of embedding vectors.
    return [embedding.values for embedding in response.embeddings]


def build_chroma_collection():
    """Create or refresh the local ChromaDB collection."""
    # Chroma stores the vector database files in this local folder.
    client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))

    # Delete the old collection so ingestion always matches the latest documents.
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except ValueError:
        # Chroma raises ValueError when the collection does not exist yet.
        pass

    # Create a fresh collection for this project.
    collection = client.create_collection(name=COLLECTION_NAME)

    return collection


def ingest_documents():
    """Load, chunk, embed, and save documents into ChromaDB."""
    documents = load_documents()

    # Stop early with a helpful message if there are no files to ingest.
    if not documents:
        print("No .txt or .md files found in the documents folder.")
        print("Add your files to documents/, then run: python ingest.py")
        return

    collection = build_chroma_collection()

    ids = []
    chunks = []
    metadatas = []

    # Convert each document into chunks that can be embedded and searched.
    for document_index, document in enumerate(documents):
        document_chunks = split_text(document["text"])

        for chunk_index, chunk in enumerate(document_chunks):
            # Each chunk needs a unique ID inside ChromaDB.
            chunk_id = f"doc-{document_index}-chunk-{chunk_index}"

            ids.append(chunk_id)
            chunks.append(chunk)

            # Metadata lets us show which file a retrieved chunk came from.
            metadatas.append({"source": document["source"]})

    # Create Gemini embeddings before saving chunks into ChromaDB.
    embeddings = embed_texts(chunks)

    # Add chunks and their Gemini embeddings to the local ChromaDB database.
    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print(f"Ingested {len(chunks)} chunks from {len(documents)} documents.")
    print("Your local ChromaDB knowledge base is ready.")


if __name__ == "__main__":
    # Running this file directly builds the vector database.
    ingest_documents()
