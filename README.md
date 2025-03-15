English | [中文](README_zh.md) | [한국어](README_ko.md) | [日本語](README_ja.md)

[![GitHub stars](https://img.shields.io/github/stars/mannaandpoem/OpenManus?style=social)](https://github.com/mannaandpoem/OpenManus/stargazers)
&ensp;
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) &ensp;
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)

# OpenManus

OpenManus is an open-source framework for building versatile AI agents capable of solving complex tasks using multiple tools and planning capabilities.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key Components](#key-components)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Available Tools](#available-tools)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

## Architecture Overview

OpenManus is built on a modular architecture that separates concerns between agents, flows, tools, and the language model interface. This design enables flexibility, extensibility, and reusability of components.

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenManus System                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                           User Input                            │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                             Flow                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ Plan Creation│ → │Step Execution│ → │   Plan Finalization  │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                            Agents                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │    Manus    │    │   Planning   │    │      ToolCall       │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                            Tools                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ Web Search  │    │ Python Exec │    │    Browser Use      │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ File Saver  │    │  Terminal   │    │      Planning       │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Language Model (LLM)                      │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### Agents

Agents are the core entities that process user requests and execute actions. OpenManus provides several agent types:

1. **BaseAgent**: The abstract foundation for all agents, providing state management and execution flow.
2. **ReActAgent**: Implements the Reasoning and Acting pattern for problem-solving.
3. **ToolCallAgent**: Extends ReActAgent with the ability to use external tools.
4. **Manus**: The primary user-facing agent that combines multiple capabilities.

### Flows

Flows orchestrate the execution of complex tasks by breaking them down into manageable steps:

1. **BaseFlow**: The foundation for all flows, providing basic flow control.
2. **PlanningFlow**: Creates and executes plans with multiple steps, using appropriate agents for each step.

### Tools

Tools extend agent capabilities by providing interfaces to external systems and functionality:

1. **Web Search**: Search the internet for information.
2. **Python Execute**: Run Python code dynamically.
3. **Browser Use**: Interact with web browsers for web automation.
4. **File Saver**: Save files to disk.
5. **Terminal**: Execute terminal commands.
6. **Planning**: Create and manage execution plans.

### LLM Interface

The LLM (Language Learning Model) interface provides a standardized way to interact with various language models, supporting different providers and configurations.

## Installation

We provide two installation methods:

### Method 1: Using conda

```bash
# Create a new conda environment
conda create -n open_manus python=3.12
conda activate open_manus

# Clone the repository
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus

# Install dependencies
pip install -r requirements.txt
```

### Method 2: Using uv (Recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Unix/macOS
# Or on Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

## Configuration

OpenManus requires configuration for the LLM APIs it uses:

1. Create a `config.toml` file in the `config` directory:

```bash
cp config/config.example.toml config/config.toml
```

2. Edit `config/config.toml` to add your API keys and customize settings:

```toml
# Global LLM configuration
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
max_tokens = 4096
temperature = 0.0

# Optional configuration for specific LLM models
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
```

## Quick Start

Run OpenManus with a single command:

```bash
python main.py
```

Then input your idea via terminal!

For the planning flow version, you can run:

```bash
python run_flow.py
```

## How It Works

OpenManus operates through a series of steps:

1. **User Input**: The user provides a prompt describing the task they want to accomplish.

2. **Planning**: The system analyzes the prompt and creates a structured plan with multiple steps.

3. **Execution**: Each step in the plan is executed by an appropriate agent using various tools.

4. **Tool Usage**: Agents use tools to interact with external systems (web, filesystem, etc.).

5. **Result Generation**: The system compiles the results of all steps and provides a comprehensive response.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   User Input    │────▶│    Planning     │────▶│   Execution     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     Result      │◀────│  Tool Usage     │◀────│  Step Processing│
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Agent Execution Cycle

Each agent follows a specific execution cycle:

1. **Think**: Analyze the current context and determine the next action.
2. **Act**: Execute the chosen action using appropriate tools.
3. **Observe**: Process the results of the action.
4. **Repeat**: Continue the cycle until the task is complete or maximum steps are reached.

```
┌─────────────────────────────────────────────────────────────────┐
│                       Agent Execution Cycle                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │      Think      │
                        └─────────────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     Observe     │◀────│       Act       │◀────│     Decide      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │
        └───────────────────────┐
                                ▼
                        ┌─────────────────┐
                        │   Task Complete?│
                        └─────────────────┘
                          /            \
                         /              \
                        /                \
                       ▼                  ▼
              ┌─────────────┐      ┌─────────────┐
              │     Yes     │      │     No      │
              └─────────────┘      └─────────────┘
                     │                    │
                     ▼                    │
              ┌─────────────┐             │
              │   Finish    │             │
              └─────────────┘             │
                                          │
                                          ▼
                                  Back to Think phase
```

## Available Tools

OpenManus includes a variety of tools that extend agent capabilities:

| Tool | Description |
|------|-------------|
| WebSearch | Search the internet for information |
| PythonExecute | Run Python code dynamically |
| BrowserUseTool | Interact with web browsers for web automation |
| FileSaver | Save files to disk |
| Terminal | Execute terminal commands |
| Planning | Create and manage execution plans |
| CreateChatCompletion | Generate text using the LLM |
| Terminate | End the execution process |

## Examples

OpenManus can handle a wide range of tasks, including:

- Web research and information gathering
- Data analysis and visualization
- Content creation and summarization
- Web automation and interaction
- File and system operations

Check the `examples` directory for sample use cases.

## Contributing

We welcome contributions to OpenManus! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure code quality
5. Submit a pull request

Before submitting a pull request, please use the pre-commit tool to check your changes:

```bash
pre-commit run --all-files
```

## License

OpenManus is released under the MIT License. See the LICENSE file for details.

---

Built with ❤️ by the OpenManus team.

## Project Demo

<video src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" data-canonical-src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="max-height:640px; min-height: 200px"></video>

## Community Group
Join our networking group on Feishu and share your experience with other developers!

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mannaandpoem/OpenManus&type=Date)](https://star-history.com/#mannaandpoem/OpenManus&Date)

## Acknowledgement

Thanks to [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
and [browser-use](https://github.com/browser-use/browser-use) for providing basic support for this project!

Additionally, we are grateful to [AAAJ](https://github.com/metauto-ai/agent-as-a-judge), [MetaGPT](https://github.com/geekan/MetaGPT), [OpenHands](https://github.com/All-Hands-AI/OpenHands) and [SWE-agent](https://github.com/SWE-agent/SWE-agent).

OpenManus is built by contributors from MetaGPT. Huge thanks to this agent community!

## Cite
```bibtex
@misc{openmanus2025,
  author = {Xinbin Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong},
  title = {OpenManus: An open-source framework for building general AI agents},
  year = {2025},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/mannaandpoem/OpenManus}},
}
```
