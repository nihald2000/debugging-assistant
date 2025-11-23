---
title: DebugGenie
emoji: 🧞
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.0.0
app_file: ui/app_hf.py
pinned: false
license: mit
---

# DebugGenie 🧞

AI-powered debugging assistant that uses a multi-agent system (Claude, Gemini, GPT-4) to analyze errors, visualize execution flow, and suggest fixes.

## Configuration

This Space acts as a frontend for the DebugGenie backend running on Modal.

**Required Secret:**
- `MODAL_API_URL`: The URL of your deployed Modal endpoint (e.g., `https://your-username--debuggenie-app-analyze-error.modal.run`).
