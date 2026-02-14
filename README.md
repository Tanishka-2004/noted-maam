# AI-Powered Meeting Summarizer

## Overview

The **AI-Powered Meeting Summarizer** is a Gradio-powered application that converts audio recordings of meetings into transcripts and provides concise summaries using `whisper.cpp` for audio-to-text conversion and `Ollama` for text summarization. This tool is ideal for quickly extracting key points, decisions, and action items from meetings.

<img width="1512" alt="Screenshot 2024-10-01 at 10 05 32 PM" src="https://github.com/user-attachments/assets/5b93cfed-c853-4ebb-8d90-bbda58354192">


https://github.com/user-attachments/assets/2f1de19d-0feb-4a35-a6ab-f9be8dabf512




## Features

- **Audio-to-Text Conversion**: Uses `whisper.cpp` to convert audio files into text.
- **Text Summarization**: Uses models from the `Ollama` server to summarize the transcript.
- **Multiple Models Support**: Supports different Whisper models (`base`, `small`, `medium`, `large-V3`) and any available model from the Ollama server.
- **Translation**: Allows translation of non-English audio to English using Whisper.
- **Gradio Interface**: Provides a user-friendly web interface to upload audio files, view summaries, and download transcripts.

## Requirements

- Python 3.x
- [FFmpeg](https://www.ffmpeg.org/) (for audio processing)
- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) (for audio-to-text conversion)
- [Ollama server](https://ollama.com/) (for text summarization)
- [Gradio](https://www.gradio.app/) (for the web interface)
- [Requests](https://requests.readthedocs.io/en/latest/) (for handling API calls to the Ollama server)

