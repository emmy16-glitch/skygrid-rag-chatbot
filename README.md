# SkyGrid RAG Chatbot

SkyGrid RAG Chatbot is a beginner-friendly Python chatbot that answers questions using your own text documents.

RAG means Retrieval-Augmented Generation. The chatbot first retrieves useful document chunks, then sends those chunks with your question to Gemini so the answer is based on your files.

## What This Project Does

- Loads `.txt` and `.md` files from the `documents` folder.
- Splits long documents into smaller chunks.
- Creates embeddings for each chunk using Gemini.
- Stores the Gemini embeddings locally in a ChromaDB folder.
- Lets you ask questions from the terminal or through a FastAPI web API.
- Retrieves the most relevant chunks for your question.
- Sends the retrieved context and your question to Gemini.
- Answers using the retrieved document context.

## Project Files

- `app.py` starts the terminal chatbot and exposes the FastAPI `/chat` endpoint.
- `ingest.py` loads your documents, chunks them, creates Gemini embeddings, and saves them locally.
- `retriever.py` searches the local vector database for relevant chunks.
- `requirements.txt` lists the Python packages to install.
- `documents/` is where you put your `.txt` and `.md` files.
- `chroma_db/` is created automatically after ingestion and stores the Gemini embeddings locally.

## Setup

Install the required packages:

```bash
pip3 install -r requirements.txt
```

Create a `.env` file in the project folder:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

The `GEMINI_MODEL` line is optional. If you do not add it, the app uses `gemini-2.5-flash`.

## Add Your Documents

Put your `.txt` and `.md` files inside the `documents` folder.

Example:

```text
documents/
  company_notes.txt
  project_guide.md
```

## Build the Local Knowledge Base

Run this command after adding or changing documents:

```bash
python3 ingest.py
```

This creates Gemini embeddings and saves them locally in `chroma_db/`.

## Start the Chatbot

Run:

```bash
python3 app.py
```

Then ask questions in the terminal.

To stop the chatbot, type:

```text
exit
```

or:

```text
quit
```

## Basic Workflow

1. Add `.txt` or `.md` files to `documents/`.
2. Run `python3 ingest.py`.
3. Run `python3 app.py`.
4. Ask questions about your documents.

## Start the FastAPI Web API

Run this after you have ingested your documents:

```bash
uvicorn app:api --reload --port 8001
```

The API will run at:

```text
http://127.0.0.1:8001
```

Open the root endpoint to see the welcome message and available endpoints:

```bash
curl http://127.0.0.1:8001/
```

Send a chat request:

```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is SkyGrid RAG Chatbot?"}'
```

If port `8000` is already used by another app, such as Django, use port `8001` as shown above.

Check that the API is alive:

```bash
curl http://127.0.0.1:8001/health
```

Expected response:

```json
{
  "status": "ok"
}
```

The API returns JSON like this:

```json
{
  "reply": "The chatbot answer appears here."
}
```

## Deployment

The FastAPI app object is named `api` inside `app.py`.

Use this deployment start command:

```bash
uvicorn app:api --host 0.0.0.0 --port 8001
```

Some hosts provide a dynamic `$PORT` environment variable. If your host does that, use:

```bash
uvicorn app:api --host 0.0.0.0 --port $PORT
```

Required environment variable:

```text
GEMINI_API_KEY=your_gemini_api_key_here
```

Optional environment variables:

```text
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Do not deploy or commit your `.env` file. Add the environment variables in your hosting dashboard instead.

Before deployment, run ingestion locally or during your deployment setup so `chroma_db/` exists:

```bash
python3 ingest.py
```

After deployment, test the public root and health endpoints:

```bash
curl https://your-app-url.example.com/
curl https://your-app-url.example.com/health
```

Then test the public chat endpoint:

```bash
curl -X POST https://your-app-url.example.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Playwright used for in this project?"}'
```

## WhatsApp Cloud API Webhook

This app includes WhatsApp Cloud API webhook routes:

- `GET /webhook` verifies your webhook with Meta.
- `POST /webhook` receives WhatsApp messages and replies with the RAG chatbot answer.

Add these environment variables in your hosting dashboard:

```text
WHATSAPP_VERIFY_TOKEN=choose_a_private_verify_token
WHATSAPP_ACCESS_TOKEN=your_meta_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
```

Optional WhatsApp environment variable:

```text
WHATSAPP_API_VERSION=v20.0
```

Use this callback URL in the Meta developer dashboard:

```text
https://your-app-url.example.com/webhook
```

Use the same value for Meta's verify token that you set as `WHATSAPP_VERIFY_TOKEN`.

Webhook flow:

1. Meta sends a verification request to `GET /webhook`.
2. The app checks `WHATSAPP_VERIFY_TOKEN`.
3. When a user sends a WhatsApp text message, Meta sends it to `POST /webhook`.
4. The app extracts the user's message text.
5. The message is passed into the existing RAG chatbot.
6. The chatbot reply is sent back through the WhatsApp Cloud API.

Only text messages are handled in this beginner version.

## Notes

- Run `python3 ingest.py` again whenever you add, remove, or edit documents.
- Gemini creates the embeddings, and ChromaDB stores them locally in the `chroma_db/` folder.
- Your document chunks are sent to Gemini only when you ask a question.
- The code is intentionally simple so beginners can read and modify it.
