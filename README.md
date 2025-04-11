# YouTube Video Translator & Summarizer Bot 🤖

A Telegram bot that extracts, translates, and summarizes YouTube video transcripts using:
- Supadata API for transcript extraction
- Google Gemini AI for translation & summarization
- ChromaDB for vector storage & semantic search
- LaBSE sentence transformer for embeddings

## Features ✨

- 📺 Extract YouTube video transcripts
- 🌍 Translate English transcripts to Persian (Farsi)
- 📝 Summarize video content in Persian
- 🔍 Semantic search through processed videos
- 💾 Store and retrieve translations in ChromaDB vector database

## Setup & Installation ⚙️

### Prerequisites
- Python 3.8+
- Telegram bot token
- Supadata API key
- Google Gemini API key
- HuggingFace token (for LaBSE model)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   
2.Install dependencies:

   pip install -r requirements.txt
   
3.Create .env file:

   cp .env.example .env

### Required Environment Variables
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

SUPADATA_API_KEY=your_supadata_api_key

GEMINI_API_KEY=your_gemini_api_key

HUGGINGFACE_TOKEN=your_huggingface_token

HTTP_PROXY=your_proxy_url  # if needed

HTTPS_PROXY=your_proxy_url # if needed
   
