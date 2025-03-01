# ANJ DEV Terminal - Enhanced Version

This document provides instructions on how to run and use the enhanced ANJ DEV terminal with all its new features.

## Installation

1. Clone the repository or download the source code.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Terminal

Launch the terminal by running:

```bash
python launch_terminal.py
```

This will start the ANJ DEV terminal with all the enhanced features.

## Features Overview

The enhanced ANJ DEV terminal includes the following new features:

### 1. File Management

- **Text Editor**: Edit files with syntax highlighting, line numbering, and advanced editing capabilities.
- **File Viewer**: View file contents with syntax highlighting and search functionality.
- **File Comparison**: Compare two files and see their differences.
- **File Browser**: Navigate through your project's directory structure.

### 2. Terminal Integration

- **Command Execution**: Run shell commands directly from the terminal.
- **Interactive Environment**: Interact with a shell while maintaining context about your project.
- **Output Capture**: Command outputs are captured and can be used to inform future code generation.
- **Environment Management**: Support for virtual environments in Python projects.

### 3. Testing Framework

- **Test Generation**: Generate tests for specific files or functions.
- **Test Runner**: Run tests with popular frameworks like pytest, unittest, Jest, or Mocha.
- **Test Result Visualization**: View test results with clear pass/fail indicators.
- **Coverage Analysis**: See test coverage statistics for your code.

### 4. Code Refactoring & Modification

- **Code Analysis**: Get suggestions for improving your code.
- **Refactoring Operations**: Perform common refactoring operations like renaming, extracting methods, etc.
- **Intelligent Code Edits**: Request specific changes to existing files.
- **Code Explanation**: Get explanations of code blocks or entire files in natural language.

### 5. Project Management

- **Dependency Management**: Manage project dependencies with pip, npm, etc.
- **Project Statistics**: View metrics about your project.
- **Documentation Generation**: Generate documentation from code comments.
- **Build & Run**: Execute project-appropriate build and run commands.

## Using the Features

### File Editor

To edit a file:
1. From the main menu, select "File Management" > "Edit File"
2. Use the file browser to navigate to and select the file you want to edit
3. Use the following keyboard shortcuts in the editor:
   - Arrow keys: Navigate
   - i: Enter insert mode
   - Esc: Exit insert mode
   - :w: Save file
   - :q: Quit editor
   - :wq: Save and quit

### File Viewer

To view a file:
1. From the main menu, select "File Management" > "View File"
2. Use the file browser to select the file you want to view
3. Use the following keyboard shortcuts:
   - Arrow keys: Navigate
   - /: Search
   - n: Next search result
   - N: Previous search result
   - q: Quit viewer

### File Comparison

To compare two files:
1. From the main menu, select "File Management" > "Compare Files"
2. Select the first file using the file browser
3. Select the second file using the file browser
4. Use the following keyboard shortcuts:
   - Arrow keys: Navigate
   - n: Next difference
   - p: Previous difference
   - q: Quit comparison

### Terminal

To use the integrated terminal:
1. From the main menu, select "Terminal" > "Open Terminal"
2. Enter commands as you would in a regular terminal
3. Use the following keyboard shortcuts:
   - Up/Down: Navigate command history
   - Ctrl+C: Interrupt command
   - Ctrl+D: Exit terminal
   - Ctrl+L: Clear screen

### Testing

To generate and run tests:
1. From the main menu, select "Testing" > "Generate Tests"
2. Select the file you want to generate tests for
3. The tests will be generated and saved in the appropriate location
4. To run tests, select "Testing" > "Run Tests"
5. View the test results in the output window

### Code Refactoring

To refactor code:
1. From the main menu, select "Code Refactoring" > "Analyze Code"
2. Select the file you want to analyze
3. View the suggestions and select the ones you want to apply
4. To perform specific refactoring operations, select "Code Refactoring" > "Refactor Code"
5. Choose the operation (rename, extract method, etc.) and provide the required parameters

### Project Management

To manage dependencies:
1. From the main menu, select "Project Management" > "Manage Dependencies"
2. Choose the operation (install, add, remove, update)
3. Follow the prompts to complete the operation

To generate documentation:
1. From the main menu, select "Project Management" > "Generate Documentation"
2. Choose whether to generate documentation for a specific file or the entire project
3. The documentation will be generated and saved as Markdown files

## Keyboard Shortcuts

### Global Shortcuts

- F1: Help
- F2: Open file browser
- F3: Open terminal
- F4: Run tests
- F5: Generate code
- F10: Exit

### Editor Shortcuts

- Ctrl+S: Save file
- Ctrl+Q: Quit editor
- Ctrl+F: Find in file
- Ctrl+G: Go to line
- Ctrl+Z: Undo
- Ctrl+Y: Redo
- Ctrl+X: Cut
- Ctrl+C: Copy
- Ctrl+V: Paste
- Tab: Indent
- Shift+Tab: Unindent

## Configuration

You can customize the ANJ DEV terminal by editing the `config.json` file. This allows you to:

- Set default paths
- Configure editor preferences
- Set up language-specific settings
- Customize keyboard shortcuts
- Configure LLM providers

## Troubleshooting

If you encounter any issues:

1. Check the log file at `logs/anj_dev.log`
2. Ensure all dependencies are installed correctly
3. Verify that your configuration is valid
4. Try running with the `--debug` flag: `python launch_terminal.py --debug`

## Contributing

Contributions to the ANJ DEV terminal are welcome! Please see the `CONTRIBUTING.md` file for guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.