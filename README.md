---
title: DebugGenie
emoji: 🧞
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
tags:
  - mcp
  - debugging
  - ai-agents
  - multi-agent
  - claude
  - gemini
  - gpt4
  - code-analysis
  - error-debugging
  - stack-overflow
short_description: Multi-agent AI debugging assistant with visual analysis, codebase search, and voice explanations
---

# DebugGenie 🧞

DebugGenie is an AI-powered debugging assistant that orchestrates multiple specialized agents to help you solve complex coding problems. It leverages a multi-agent architecture with visual analysis, codebase semantic search, and web search capabilities, all visualized through an interactive 3D error flow.

## 🚀 Features

- **Multi-Agent Orchestration**:
  - **Orchestrator (Claude Sonnet 4.5)**: Central reasoning engine that manages the debugging process.
  - **Visual Agent (Gemini 3.0 Flash)**: Analyzes screenshots and visual error indicators.
  - **Codebase Agent (Claude Sonnet 4.5)**: Performs semantic search over your codebase using LlamaIndex.
  - **Web Search Agent (GPT-4)**: Synthesizes solutions from the web.
- **3D Error Visualization**: Visualize the flow of errors and agent interactions using Blaxel.
- **Voice Explanations**: Get audio explanations of the debugging process via ElevenLabs.
- **MCP Support**: Integrates with Model Context Protocol (MCP) servers for filesystem access, GitHub, and more.
- **Deployment**: Ready for deployment on Modal Labs and HuggingFace Spaces.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/debuggenie.git
    cd debuggenie
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Unix/MacOS
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Copy `.env.example` to `.env` and fill in your API keys.
    ```bash
    cp .env.example .env
    ```

## 🔑 Configuration

DebugGenie uses a robust configuration system based on Pydantic.
- **API Keys**: Managed in `config/api_keys.py`. Ensure all required keys are set in your `.env` file.
- **MCP Servers**: Configure your MCP servers in `config/mcp_config.py`.

## 🏃 Usage

Run the Gradio application:

```bash
python app.py
```

Navigate to the URL provided in the console (usually `http://localhost:7860`) to interact with DebugGenie.

## 🏗️ Architecture

```mermaid
graph TD
    User[User] --> UI[Gradio UI]
    UI --> Orch[Orchestrator (Claude Sonnet 4.5)]
    Orch --> Viz[Visual Agent (Gemini 3.0)]
    Orch --> Code[Codebase Agent (Claude Sonnet 4.5)]
    Orch --> Web[Web Search Agent (GPT-4)]
    Orch --> MCP[MCP Servers]
    Orch --> Blaxel[3D Viz (Blaxel)]
    Orch --> TTS[Voice (ElevenLabs)]
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.
