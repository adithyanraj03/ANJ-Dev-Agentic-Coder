#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import threading
import time
from typing import Optional
from datetime import datetime
from queue_handler import log_queue
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QPlainTextEdit, QLabel, QPushButton, QHBoxLayout,
                           QStyle, QLineEdit, QShortcut)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRegExp
from PyQt5.QtGui import (QColor, QTextCharFormat, QFont, QPalette,
                       QTextCursor, QTextBlockFormat, QTextDocument, QKeySequence)
class LogMessage:
    """Represents a log message."""
    
    def __init__(self, message: str, level: str = 'INFO'):
        """Initialize log message."""
        self.timestamp = datetime.now()
        self.message = message
        self.level = level
        
    def __str__(self) -> str:
        """Format log message."""
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.level}: {self.message}"
        
    def get_color(self) -> int:
        """Get color pair for message level."""
        return {
            'INFO': 1,  # White
            'SUCCESS': 2,  # Green
            'WARNING': 3,  # Yellow
            'ERROR': 4,  # Red
            'DEBUG': 5,  # Blue
        }.get(self.level, 1)

    @classmethod
    def from_dict(cls, data: dict) -> 'LogMessage':
        """Create LogMessage from dictionary."""
        return cls(data.get('message', ''), data.get('level', 'INFO'))

class LogViewerWindow(QMainWindow):
    """Main log viewer window using Qt."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ANJ DEV - Log Viewer")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        toolbar_layout.setSpacing(10)
        
        # Add logo with proper styling
        logo = QLabel("╔═════ ANJ DEV ════╗\n╚══ LOGS VIEWER  ══╝")
        logo_font = QFont("Consolas", 10)
        logo_font.setBold(True)
        logo.setFont(logo_font)
        logo.setStyleSheet("color: #88CCFF;")  # Light blue color
        toolbar_layout.addWidget(logo)
        
        # Add spacer
        toolbar_layout.addStretch(1)
        
        # Add status labels
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # Debug log status
        self.debug_status = QLabel("Debug Log: Not Found")
        self.debug_status.setStyleSheet("color: #FF5555;")  # Red color
        status_layout.addWidget(self.debug_status)
        
        # Add spacer between status labels
        status_layout.addSpacing(20)
        
        # Regular status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888888;")  # Gray color
        status_layout.addWidget(self.status_label)
        
        toolbar_layout.addWidget(status_widget)
        layout.addWidget(toolbar)
        
        # Monitor debug log file status
        self.debug_log_timer = self.startTimer(1000)  # Check every second
        
        # Add controls with spacer
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(10, 0, 10, 0)
        controls_layout.setSpacing(10)
        
        # Add search box with flexible width
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search logs (Ctrl+F)...")
        search_box.textChanged.connect(self.highlight_search)
        search_box.setClearButtonEnabled(True)
        controls_layout.addWidget(search_box, stretch=1)
        
        # Add wrap toggle button
        wrap_btn = QPushButton("Word Wrap (Ctrl+W)")
        wrap_btn.setCheckable(True)
        wrap_btn.setToolTip("Toggle word wrapping (Ctrl+W)")
        wrap_btn.clicked.connect(self.toggle_wrap)
        controls_layout.addWidget(wrap_btn)
        
        # Add clear button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.setToolTip("Clear all logs (Ctrl+L)")
        clear_btn.clicked.connect(self.clear_logs)
        controls_layout.addWidget(clear_btn)
        
        # Add controls to main layout
        layout.addWidget(controls)
        
        # Track log count
        self.log_count = 0

        # Set keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self, search_box.setFocus)
        QShortcut(QKeySequence("Ctrl+W"), self, lambda: wrap_btn.click())
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_logs)
        
        # Create log display with syntax highlighting
        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumBlockCount(100000)  # Limit for performance
        
        # Set monospace font
        font = QFont("Consolas", 10)
        self.log_display.setFont(font)
        
        # Setup colors
        self.colors = {
            'INFO': QColor(200, 200, 200),     # Light gray
            'SUCCESS': QColor(0, 255, 0),      # Green
            'WARNING': QColor(255, 255, 0),    # Yellow
            'ERROR': QColor(255, 50, 50),      # Red
            'DEBUG': QColor(100, 150, 255),    # Light blue
            'JSON': QColor(255, 200, 100),     # Orange for JSON
            'TIMESTAMP': QColor(150, 150, 150), # Dark gray
            'SEPARATOR': QColor(100, 100, 100), # Divider color
            'RAW': QColor(180, 180, 180),      # Light gray for raw data
            'COMMAND': QColor(0, 255, 255),    # Cyan for commands
        }
        
        # Set dark theme
        palette = self.log_display.palette()
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.Text, QColor(200, 200, 200))
        self.log_display.setPalette(palette)
        
        layout.addWidget(self.log_display)
        
        # Start log monitor thread
        self.monitor_thread = LogMonitorThread()
        self.monitor_thread.new_log.connect(self.add_log)
        self.monitor_thread.start()
        
        # Show window
        self.show()
        
    def timerEvent(self, event):
        """Handle timer events to update debug log status."""
        if event.timerId() == self.debug_log_timer:
            if os.path.exists("agent_debug.log"):
                self.debug_status.setText("Debug Log: Active")
                self.debug_status.setStyleSheet("color: #55FF55;")  # Green color
            else:
                self.debug_status.setText("Debug Log: Not Found")
                self.debug_status.setStyleSheet("color: #FF5555;")  # Red color
    
    def add_log(self, message: dict):
        """Add a new log message to display with enhanced raw data."""
        try:
            level = message.get('level', 'INFO')
            text = message.get('message', '')
            raw_data = message.get('raw_data', None)
            source = message.get('source', '')
            
            # Get document and cursor
            document = self.log_display.document()
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.End)
            cursor.beginEditBlock()
            
            # Add timestamp with color
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
            fmt = QTextCharFormat()
            fmt.setForeground(self.colors['TIMESTAMP'])
            cursor.insertText(f"[{timestamp}] ", fmt)
            
            # Increment log count and update status
            self.log_count += 1
            self.update_status()
            
            # Add level and source with color
            fmt.setForeground(self.colors.get(level, self.colors['INFO']))
            if source == 'debug_log':
                cursor.insertText("[AGENT] ", fmt)  # Add special prefix for debug logs
                # Keep original timestamp if exists in debug log
                timestamp_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', text)
                if timestamp_match:
                    text = text[timestamp_match.end():].strip()
            
            # Handle special formatting for JSON, raw responses and various data types
            if "Raw" in text or "raw data" in text.lower() or raw_data:
                self._format_raw_content(cursor, text, raw_data)
            # Special formatting for action start/end
            elif text.startswith("=== START:") or text.startswith("=== END:"):
                # Format action headers with bold + color
                fmt.setFontWeight(QFont.Bold)
                if "START:" in text:
                    fmt.setForeground(QColor(100, 255, 100))  # Bright green
                else:
                    if "(SUCCESS)" in text:
                        fmt.setForeground(QColor(100, 255, 100))  # Bright green
                    else:
                        fmt.setForeground(QColor(255, 100, 100))  # Bright red
                
                cursor.insertText(text + '\n', fmt)
            # Special formatting for files and paths
            elif ": /" in text or text.endswith(".py") or text.endswith(".json"):
                parts = text.split(": ", 1)
                if len(parts) > 1:
                    # Format the description part
                    fmt.setForeground(self.colors.get(level, self.colors['INFO']))
                    cursor.insertText(f"{parts[0]}: ", fmt)
                    
                    # Format the path part
                    fmt.setForeground(QColor(255, 200, 100))  # Orange for paths
                    cursor.insertText(f"{parts[1]}\n", fmt)
                else:
                    fmt.setForeground(self.colors.get(level, self.colors['INFO']))
                    cursor.insertText(text + '\n', fmt)
            # Commands
            elif text.startswith("Running command:") or text.startswith("Command:"):
                parts = text.split(": ", 1)
                if len(parts) > 1:
                    # Format the description part
                    fmt.setForeground(self.colors.get(level, self.colors['INFO']))
                    cursor.insertText(f"{parts[0]}: ", fmt)
                    
                    # Format the command part
                    fmt.setForeground(self.colors['COMMAND'])
                    cursor.insertText(f"{parts[1]}\n", fmt)
                else:
                    fmt.setForeground(self.colors.get(level, self.colors['INFO']))
                    cursor.insertText(text + '\n', fmt)
            else:
                fmt.setForeground(self.colors.get(level, self.colors['INFO']))
                cursor.insertText(text + '\n', fmt)
            
            # Add separator
            fmt.setForeground(self.colors['SEPARATOR'])
            cursor.insertText('-' * 80 + '\n', fmt)
            
            cursor.endEditBlock()
            
            # Scroll to bottom if near bottom
            sb = self.log_display.verticalScrollBar()
            if sb.value() >= sb.maximum() - 10:
                sb.setValue(sb.maximum())
            
        except Exception as e:
            print(f"Error adding log: {e}")

    def _format_raw_content(self, cursor, text, raw_data=None):
        """Format raw content with better formatting and syntax highlighting."""
        fmt = QTextCharFormat()
        
        # Add header
        fmt.setForeground(self.colors['DEBUG'])
        cursor.insertText(f"{text}\n", fmt)
        
        # Format raw data if provided
        if raw_data:
            try:
                if isinstance(raw_data, dict) or isinstance(raw_data, list):
                    import json
                    formatted_json = json.dumps(raw_data, indent=2)
                    
                    # Add JSON with syntax highlighting
                    fmt.setForeground(self.colors['JSON'])
                    block_fmt = QTextBlockFormat()
                    block_fmt.setBackground(QColor(40, 40, 40))  # Slightly lighter background
                    cursor.setBlockFormat(block_fmt)
                    cursor.insertText(formatted_json + '\n', fmt)
                else:
                    # For non-JSON raw data
                    fmt.setForeground(self.colors['RAW'])
                    cursor.insertText(str(raw_data) + '\n', fmt)
            except:
                fmt.setForeground(self.colors['RAW'])
                cursor.insertText(str(raw_data) + '\n', fmt)
        # Try to detect and format JSON in the text
        elif ":" in text and ("{" in text or "[" in text):
            parts = text.split(":", 1)
            if len(parts) > 1 and (parts[1].strip().startswith("{") or parts[1].strip().startswith("[")):
                try:
                    content = parts[1].strip()
                    import json
                    parsed = json.loads(content)
                    formatted_json = json.dumps(parsed, indent=2)
                    
                    # Add JSON with syntax highlighting
                    fmt.setForeground(self.colors['JSON'])
                    block_fmt = QTextBlockFormat()
                    block_fmt.setBackground(QColor(40, 40, 40))  # Slightly lighter background
                    cursor.setBlockFormat(block_fmt)
                    cursor.insertText(formatted_json + '\n', fmt)
                except:
                    # If JSON parsing fails, just show the raw text
                    fmt.setForeground(self.colors['RAW'])
                    cursor.insertText(parts[1] + '\n', fmt)
        else:
            # For all other raw content
            fmt.setForeground(self.colors['RAW'])
            cursor.insertText('\n', fmt)  # Add extra line break for formatting

    def highlight_search(self, text: str):
        """Highlight searched text in logs."""
        if not text:
            # Reset highlighting
            self.log_display.setPlainText(self.log_display.toPlainText())
            self.update_status()
            return

        # Save cursor position
        cursor = self.log_display.textCursor()
        saved_position = cursor.position()

        # Highlight all matches
        document = self.log_display.document()
        highlighter = QTextCharFormat()
        highlighter.setBackground(QColor(100, 100, 0))  # Dark yellow background
        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        
        match_count = 0
        while not cursor.isNull() and not cursor.atEnd():
            cursor = document.find(text, cursor)
            if not cursor.isNull():
                cursor.mergeCharFormat(highlighter)
                match_count += 1
                
        cursor.endEditBlock()

        # Restore cursor position
        cursor.setPosition(saved_position)
        self.log_display.setTextCursor(cursor)
        
        # Update status with match count
        self.update_status(match_count)

    def toggle_wrap(self, checked: bool):
        """Toggle word wrap mode."""
        self.log_display.setLineWrapMode(
            QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap
        )

    def clear_logs(self):
        """Clear all logs."""
        self.log_display.clear()
        log_queue.clear()
        self.log_count = 0
        self.update_status()

    def update_status(self, search_matches: int = None):
        """Update status label with log count and search matches."""
        status_text = f"Total logs: {self.log_count}"
        if search_matches is not None:
            status_text += f" | Search matches: {search_matches}"
        self.status_label.setText(status_text)

class LogMonitorThread(QThread):
    """Thread to monitor log queue and debug file."""
    new_log = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.last_position = 0
        self.debug_file = "agent_debug.log"
        
    def run(self):
        """Monitor log queue and debug file for new messages."""
        while True:
            try:
                # Check queue messages
                try:
                    message = log_queue.get_nowait()
                    if message:
                        self.new_log.emit(message)
                except:
                    pass
                
                # Check debug file
                if os.path.exists(self.debug_file):
                    with open(self.debug_file, 'r') as f:
                        f.seek(self.last_position)
                        new_content = f.read()
                        if new_content:
                            # Split into lines and send each as a log message
                            lines = new_content.splitlines()
                            for line in lines:
                                if line.strip():
                                    # Parse log level if present
                                    level = 'DEBUG'
                                    if '[INFO]' in line:
                                        level = 'INFO'
                                    elif '[ERROR]' in line:
                                        level = 'ERROR'
                                    elif '[WARNING]' in line:
                                        level = 'WARNING'
                                        
                                    self.new_log.emit({
                                        'message': line,
                                        'level': level,
                                        'source': 'debug_log'
                                    })
                        self.last_position = f.tell()
                        
            except Exception as e:
                print(f"Log monitor error: {e}")
            
            time.sleep(0.1)  # Small delay to prevent high CPU usage
class LogWindow:
    """Handles log display in a separate window."""
    
    def __init__(self):
        """Initialize log window."""
        self.running = False
        self.window_thread: Optional[threading.Thread] = None
        self.app = None
        self.viewer = None
        
    def start(self):
        """Start log window."""
        if not self.running:
            self.running = True
            self.window_thread = threading.Thread(target=self._run_viewer)
            self.window_thread.daemon = True
            self.window_thread.start()
            
    def stop(self):
        """Stop log window."""
        self.running = False
        if self.app:
            self.app.quit()
        log_queue.clear()
        if self.window_thread:
            self.window_thread.join(timeout=1)
            
    def log(self, message: str, level: str = 'INFO'):
        """Add message to log queue."""
        if self.running:
            log_queue.put({"message": message, "level": level})
            
    def _run_viewer(self):
        """Run the Qt log viewer."""
        try:
            self.app = QApplication([])
            self.viewer = LogViewerWindow()
            self.app.exec_()
        except Exception as e:
            with open('log_viewer_errors.txt', 'a') as f:
                f.write(f"{datetime.now()}: {str(e)}\n")
        finally:
            self.running = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = LogViewerWindow()
    sys.exit(app.exec_())
