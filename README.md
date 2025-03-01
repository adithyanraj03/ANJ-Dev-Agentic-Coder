# ANJ-Dev-Agentic-Coder

# ANJ Dev

*An agentic autonomous coding assistant fine tuned for local light-weight LLMS with enhanced features for file management, terminal integration, testing, code refactoring, and project management.*

![ANJ Dev Logo](https://github.com/user-attachments/assets/a17df1d5-5269-440e-8729-2e924adb0696)


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
   ![image](https://github.com/user-attachments/assets/46033326-f5b6-4be9-8051-847180a1e0a3)

   <br>Configured for LLM-Studio , 
   <br>works best with models : 
   1. phi-3.1-mini-128k-instruct ; card : https://huggingface.co/lmstudio-community/Phi-3.1-mini-128k-instruct-GGUF
   2. phi-3-mini-4k-instruct ; card : https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf
   3. deepseek-r1-distill-qwen-7b ; card : https://huggingface.co/lmstudio-community/DeepSeek-R1-Distill-Qwen-7B-GGUF
   <br>
   or use Google Studio Free Experimental models via API  

4. Usage

   1. Run the application:
   ```bash
   python launch_terminal.py
   ```
   ![image](https://github.com/user-attachments/assets/aa9015cf-695e-400b-bbd7-f206ccb055ec)
   
   2. Select project directory 
   ![image](https://github.com/user-attachments/assets/b5094ff7-9502-448d-b03d-07fc1ebcdc59)
   
   3.choose ro create a sub directory , will be created in project dir 
   ![image](https://github.com/user-attachments/assets/259db97d-e573-48a9-8369-a0ef30677237)

   4.Main menu 
   ![image](https://github.com/user-attachments/assets/b513e3aa-ec58-49a3-95ac-10be0caec44a)
   
   5.Toggle Log Viwer for better Understanding 
   ![image](https://github.com/user-attachments/assets/b058747e-3ff0-40fb-876c-bb0ce5d7a555)
   6.New Session Enter the request (example :create a snake game using python ) [Accept (y) , Reject (n) , Edit (e) ]
   <img width="950" alt="image" src="https://github.com/user-attachments/assets/30b96ae5-12e7-40b6-8ad9-f99cb894863f" />
   ![image](https://github.com/user-attachments/assets/79d91130-efa4-46b7-aa5b-baf67d0bc0f1)
   ![image](https://github.com/user-attachments/assets/6eead0da-5ba3-413a-9c96-dafdf35fcb6c)
   ![image](https://github.com/user-attachments/assets/14990543-a8df-4b05-bbc9-3ca406b20464)
   ![image](https://github.com/user-attachments/assets/1ff4515a-c882-498b-ba2d-5436273fcef7)
   ![image](https://github.com/user-attachments/assets/955d3b6a-34a4-45ef-9765-f93105557067)
   ![image](https://github.com/user-attachments/assets/25133d3c-d953-4367-8e26-3888670772dd)
   <br>
   Edit read feature :
   ![image](https://github.com/user-attachments/assets/f5039dd2-f266-48df-9166-f9df10640b55)
   ![image](https://github.com/user-attachments/assets/1d320fbc-8627-4542-a59a-35fb07a6eb73)
   ![image](https://github.com/user-attachments/assets/09f627e4-1104-4d0c-ab13-0181add798d4)

   
   other Interactive apps make by the ANJ Dev +  DeepSeek-R1-Distill-Qwen-7B-GGUF
   ![Recording2025-03-01074921-ezgif com-video-to-gif-converter](https://github.com/user-attachments/assets/24a38376-37e9-4987-aa4c-33e4475ce7c3)






   

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

- Anthropic, and Google for their AI models
- The Python community for the excellent libraries used in this project

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the LICENSE file for details.



