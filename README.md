# ANJ-Dev-Agentic-Coder

# ANJ Dev

*An agentic autonomous coding assistant fine tuned for local light-weight LLMS with enhanced features for file management, terminal integration, testing, code refactoring, and project management.*

![ANJ Dev Logo](logo.png)

## Overview

ANJ Dev is an autonomous coding agent that integrates with lightweight local LLMs to provide coding assistance that respects your workflow and privacy. The agent can create and edit files, run commands, browse the web, and perform various development tasks - all while seeking your permission at each step.

## Purpose

The main purpose of ANJ Dev is to provide deep insights into how LLMs interact with agentic programming frameworks. By exposing the backend processes through comprehensive logging, the system allows developers to:

- Observe how the LLM responds to agent instructions in real-time
- Understand the detailed inner workings of the agent-LLM interaction
- View both the agent logs and LLM Studio logs simultaneously
- Optimize prompt engineering and agent architecture based on live observations
- Study the decision-making process of AI agents with full transparency
- Develop more efficient and effective agentic systems through empirical analysis

This transparency makes ANJ Dev an invaluable tool for both development and research purposes, enabling clearer optimization paths and better understanding of autonomous AI systems.

## Getting Started
## Key Features

- **Works with Local LLMs**: Designed to integrate seamlessly with lightweight local language models
- **Permission-Based Actions**: Always asks for your approval before taking actions on your system
- **File Management**: Creates, edits, and organizes files based on your requirements
- **Command Execution**: Runs terminal commands to help with development tasks
- **Persistent Memory**: Maintains context across sessions with a local memory store
- **Browser Integration**: Can search the web for solutions and documentation when needed
- **Session Management**: Create new sessions or resume previous ones as needed
- **Transparent Logging**: Comprehensive logging of both agent operations and LLM responses


## Features in Detail

### File Management

- **Text Editor**: Edit files with syntax highlighting, line numbering, and advanced editing operations
- **File Viewer**: View file contents with syntax highlighting and search capabilities
- **File Comparison**: Compare two files and see their differences
- **File Browser**: Navigate through your project's directory structure

### Terminal Integration

- **Command Execution**: Run shell commands directly from the terminal
- **Interactive Environment**: Interact with a shell while maintaining context about your project
- **Output Capture**: Command outputs are captured for context-aware code generation
- **Environment Management**: Support for virtual environments in Python projects

### Testing Framework

- **Test Generation**: Generate tests for specific files or functions
- **Test Runner**: Run tests with popular frameworks like pytest, unittest, Jest, or Mocha
- **Test Result Visualization**: View test results with clear pass/fail indicators
- **Coverage Analysis**: See test coverage statistics for your code

### Code Refactoring & Modification

- **Code Analysis**: Get suggestions for improving your code
- **Refactoring Operations**: Perform common refactoring operations like renaming, extracting methods, etc.
- **Intelligent Code Edits**: Request specific changes to existing files
- **Code Explanation**: Get explanations of code blocks or entire files in natural language

### Project Management

- **Dependency Management**: Manage project dependencies with pip, npm, etc.
- **Project Statistics**: View metrics about your project
- **Documentation Generation**: Generate documentation from code comments
- **Build & Run**: Execute project-appropriate build and run commands

### AI Integration

- **Context-Aware Suggestions**: AI understands your project context for better code generation
- **Inline Completions**: Get completions for specific code sections
- **Debugging Assistance**: Get suggestions for fixing runtime errors
- **Learning from Edits**: Session context updates when files are modified

### Prerequisites

- Python 3.8+
- Local LLM setup (compatible with various providers)
- Required Python packages (see `requirements.txt`)
- For JavaScript/TypeScript support: Node.js and npm/yarn

## Configuration

ANJ DEV Terminal can be customized through the `config.json` file. You can configure:

- Editor preferences
- Terminal settings
- Testing frameworks
- AI providers
- Keyboard shortcuts
- And more


### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/adithyanraj03/ANJ-Dev-Agentic-Coder.git
   cd anjdev
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your LLM provider in the settings

### Usage

Run the application:
```bash
python launch_terminal.py
```

The application will:
1. Display the ANJ Dev logo
2. Ask if you want to create a subfolder for your project
3. Automatically create a memory folder to maintain context
4. Present the main interface with options:
   - New Session
   - Resume Session
   - Toggle Log Window
   - Provider Settings

## Current Status & Roadmap

### Current Capabilities
- Basic UI with session management
- LLM integration for code generation
- File creation functionality
- Local memory storage
- Live logging of agent and LLM interactions

### Under Development
- Improved context awareness
- More robust codebase analysis
- Enhanced file manipulation
- Command execution reliability
- Better agent reasoning and planning
- Extended browsing capabilities
- Advanced metrics for LLM-agent interaction analysis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- OpenAI, Anthropic, and Google for their AI models
- The Python community for the excellent libraries used in this project
- All contributors who have helped improve this tool

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the LICENSE file for details.



