# Audio Customer Support Agent

## Overview

This project implements a complete end-to-end Audio Customer Support Agent using the following pipeline:

```text
Speech-to-Text (STT) → Retrieval-Augmented Generation (RAG/LLM) → Text-to-Speech (TTS)
```

The system accepts audio input from the user, converts speech into text, retrieves relevant customer support information using RAG, generates a response, converts the response back into audio, and returns both transcript and audio output.

This implementation was completed as part of the company assignment and follows the restriction guidelines by avoiding prohibited high-level conversational AI frameworks.

---

# Features

- Speech-to-Text using OpenAI Whisper
- Retrieval-Augmented Generation using ChromaDB + LangChain
- Text-to-Speech using Edge TTS + Offline fallback
- FastAPI backend server
- Streamlit web interface
- Audio + transcript response
- Processing time tracking
- Customer support knowledge base
- Health monitoring endpoint
- End-to-end audio pipeline

---

# Architecture

```text
User Audio Input
        ↓
Speech-to-Text (Whisper)
        ↓
RAG Search (ChromaDB)
        ↓
LLM Response Generation
        ↓
Text-to-Speech (Edge TTS)
        ↓
Audio Response Output
```

---

# Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | Streamlit |
| STT | OpenAI Whisper |
| Vector DB | ChromaDB |
| RAG Framework | LangChain |
| TTS | Edge TTS |
| Audio Processing | FFmpeg |
| Language | Python |

---

# Project Structure

```text
audio_support_agent/
│
├── src/
│   ├── api/
│   │   └── server.py
│   │
│   ├── llm/
│   │   └── agent.py
│   │
│   ├── stt/
│   │   └── base_stt.py
│   │
│   ├── tts/
│   │   └── base_tts.py
│   │
│   ├── utils/
│   │   └── kb_test.py
│   │
│   └── pipeline.py
│
├── chroma_db/
├── docs/
├── screenshots/
├── requirements.txt
├── streamlit_app.py
├── README.md
└── submission_notes.md
```

---

# Setup Instructions

## 1. Extract the Project

Extract the project zip file.

Open terminal / PowerShell and move into the project directory.

Example:

```powershell
cd C:\Users\samra\Downloads\audio_support_agent_final_transcript_text_fixed\audio_support_agent
```

---

# Create Virtual Environment

## Windows

```powershell
python -m venv venv
```

Activate virtual environment:

```powershell
venv\Scripts\activate
```

---

## Mac/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

- FastAPI
- Streamlit
- Whisper
- ChromaDB
- LangChain
- Edge TTS
- Supporting libraries

---

# Install FFmpeg

FFmpeg is required for Whisper audio processing.

## Windows

Install using winget:

```powershell
winget install Gyan.FFmpeg
```

Verify installation:

```powershell
ffmpeg -version
```

If FFmpeg is installed correctly, version information will be displayed.

---

# Running the Project

The project requires two terminals.

---

## Terminal 1 — Start FastAPI Backend

```powershell
cd C:\Users\samra\Downloads\audio_support_agent_final_transcript_text_fixed\audio_support_agent
python -m src.api.server
```

Expected output:

```text
Pipeline initialized successfully.
Application startup complete.
```

Backend runs on:

```text
http://localhost:8000
```

Keep this terminal open.

---

## Terminal 2 — Start Streamlit Frontend

```powershell
cd C:\Users\samra\Downloads\audio_support_agent_final_transcript_text_fixed\audio_support_agent
streamlit run streamlit_app.py
```

Open browser:

```text
http://localhost:8501
```

---

# Testing the Application

## Text Chat Testing

Example questions:

```text
What is your return policy?
How long does shipping take?
Do you provide warranty?
Can I cancel my order?
What payment methods are accepted?
How can I contact support?
```

Expected result:
- Agent returns customer-support response
- Response retrieved using RAG

---

## Audio Chat Testing

1. Upload or record audio
2. Whisper converts speech to text
3. ChromaDB retrieves relevant documents
4. Agent generates response
5. Edge TTS converts response to audio
6. UI displays:
   - User transcript
   - Agent text response
   - Audio playback
   - Processing time

Expected flow:

```text
Audio → STT → RAG/LLM → TTS → Audio Response
```

---

# Enhanced Transcript Features

The enhanced version includes:

- Transcript generation
- User speech transcript
- Agent response transcript
- Base64 encoded audio response
- Processing time metrics
- Transcript display inside Streamlit UI

Example API response:

```json
{
  "success": true,
  "audio_response": "base64_audio_data",
  "response_text": "We offer a 30-day return policy...",
  "transcript": {
    "user_input": "What is your return policy?",
    "agent_response": "We offer a 30-day return policy..."
  },
  "processing_time_ms": 2050
}
```

---

# API Endpoints

## Health Endpoint

```http
GET /health
```

Test:

```bash
curl http://localhost:8000/health
```

---

## Text Chat Endpoint

```http
POST /chat/text
```

Windows:

```powershell
curl -X POST http://localhost:8000/chat/text ^
-H "Content-Type: application/json" ^
-d "{\"text\":\"What is your return policy?\"}"
```

Mac/Linux:

```bash
curl -X POST http://localhost:8000/chat/text \
-H "Content-Type: application/json" \
-d '{"text":"What is your return policy?"}'
```

---

## Audio Chat Endpoint

```http
POST /chat/audio
```

Windows:

```powershell
curl -X POST http://localhost:8000/chat/audio ^
-F "audio=@question.wav"
```

Mac/Linux:

```bash
curl -X POST http://localhost:8000/chat/audio \
-F "audio=@question.wav"
```

Expected result:
- Audio response
- Transcript
- Processing time
- Agent response text

---

# Components Implemented

## 1. RAG Search

Implemented semantic document retrieval using:

- ChromaDB
- LangChain
- Embeddings

---

## 2. Speech-to-Text

Implemented using OpenAI Whisper.

Features:
- Local STT processing
- Audio transcription
- FFmpeg support
- Windows temp-file handling fix

---

## 3. Text-to-Speech

Implemented using:
- Edge TTS
- Offline fallback support

Features:
- Audio generation
- MP3 playback
- Fallback handling when internet fails

---

## 4. Pipeline Integration

Complete pipeline implemented:

```text
Audio Input → STT → RAG/LLM → TTS → Audio Output
```

---

# Screenshots Folder

Recommended structure:

```text
screenshots/
├── 01_server_running.png
├── 02_streamlit_ui.png
├── 03_text_chat.png
├── 04_audio_chat.png
├── 05_transcript_display.png
└── 06_health_status.png
```

---

# Common Issues & Fixes

## FFmpeg Not Found

Error:

```text
ffmpeg is not recognized
```

Fix:

```powershell
winget install Gyan.FFmpeg
```

Then restart terminal.

---

## Streamlit File Not Found

Error:

```text
File does not exist: streamlit_app.py
```

Fix:

Move into correct project folder:

```powershell
cd audio_support_agent
```

Then run:

```powershell
streamlit run streamlit_app.py
```

---

## Edge TTS Connection Error

Error:

```text
Cannot connect to speech.platform.bing.com
```

Fix:
- Offline fallback TTS already included
- Restart backend server

---

# Assignment Requirements Coverage

| Requirement | Status |
|---|---|
| RAG Implementation | Completed |
| STT Implementation | Completed |
| TTS Implementation | Completed |
| Pipeline Integration | Completed |
| Transcript Enhancement | Completed |
| Audio + Transcript Response | Completed |
| Streamlit UI Enhancement | Completed |
| Processing Time Metrics | Completed |
| Health Endpoint | Completed |
| End-to-End Audio Workflow | Completed |

---

# Final Submission Checklist

Before submission ensure:

- Backend server starts successfully
- Streamlit UI works
- Text chat works
- Audio chat works
- Transcript is displayed
- Audio playback works
- Processing time displayed
- Screenshots included
- README included
- requirements.txt included

---

# Notes

- This implementation avoids prohibited conversational AI frameworks.
- The project uses modular independently implemented components.
- Whisper is used locally for STT.
- ChromaDB is used for RAG retrieval.
- Edge TTS is used for speech synthesis with offline fallback support.

---

# Author

Submitted as part of the Audio Customer Support Agent Assignment.
