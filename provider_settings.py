#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from colorama import Fore, Style
import curses
from curses import textpad

class ProviderSettings:
    """Manage LLM provider settings and configuration."""
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = Path(config_path)
        self.load_config()

    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = self._get_default_config()
            self.save_config()

    def save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "llm_providers": {
                "local": {
                    "url": "http://localhost:1234/v1",
                    "active": True,
                    "models": ["codellama-7b-instruct"],
                    "timeout": null
                },
                "vscode": {
                    "active": False,
                    "extension_id": "GitHub.copilot",
                    "timeout": 10
                },
                "gemini": {
                    "active": False,
                    "api_key": "",
                    "model": "gemini-pro",
                    "timeout": 30
                }
            }
        }

    def show_settings_ui(self, stdscr):
        """Display interactive settings UI."""
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Title
            title = "LLM Provider Settings"
            stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
            
            # Provider list
            row = 2
            providers = self.config['llm_providers']
            for provider_name, settings in providers.items():
                active = settings.get('active', False)
                status = "✓" if active else "✗"
                color = curses.color_pair(2) if active else curses.color_pair(3)
                
                stdscr.addstr(row, 2, f"{provider_name.title()}: ", curses.A_BOLD)
                stdscr.addstr(f"[{status}]", color)
                row += 1
                
                # Show settings
                for key, value in settings.items():
                    if key != 'active':
                        stdscr.addstr(row, 4, f"{key}: {value}")
                        row += 1
                row += 1
            
            # Menu
            menu_items = [
                "1. Toggle Provider",
                "2. Edit Settings",
                "3. Test Connection",
                "4. Save & Exit"
            ]
            
            for i, item in enumerate(menu_items):
                stdscr.addstr(height - len(menu_items) + i - 1, 2, item)
            
            stdscr.refresh()
            
            # Handle input
            choice = stdscr.getch()
            if choice == ord('1'):
                self._toggle_provider_menu(stdscr)
            elif choice == ord('2'):
                self._edit_settings_menu(stdscr)
            elif choice == ord('3'):
                self._test_connections(stdscr)
            elif choice == ord('4'):
                self.save_config()
                break

    def _toggle_provider_menu(self, stdscr):
        """Menu for enabling/disabling providers and models."""
        while True:
            stdscr.clear()
            providers = self.config['llm_providers']
            
            # Show providers and their models
            row = 0
            stdscr.addstr(row, 2, "Toggle Providers and Models", curses.A_BOLD)
            row += 2
            
            provider_rows = {}  # Store row numbers for providers
            for i, (name, settings) in enumerate(providers.items(), 1):
                provider_rows[i] = row
                active = settings.get('active', False)
                status = "Enabled" if active else "Disabled"
                color = curses.color_pair(2) if active else curses.color_pair(3)
                stdscr.addstr(row, 2, f"{i}. {name.title()}: ")
                stdscr.addstr(status, color)
                row += 1
                
                # Show models if provider has any
                if 'models' in settings and settings['models']:
                    model_status = settings.get('active_models', settings['models'])
                    for j, model in enumerate(settings['models'], 1):
                        is_active = model in model_status
                        status = "✓" if is_active else "✗"
                        color = curses.color_pair(2) if is_active else curses.color_pair(3)
                        stdscr.addstr(row, 4, f"{i}.{j}. {model}: ")
                        stdscr.addstr(f"[{status}]", color)
                        row += 1
                row += 1
            
            stdscr.addstr(row + 1, 2, "Enter number to toggle provider (e.g., 1)")
            stdscr.addstr(row + 2, 2, "Enter number.number to toggle model (e.g., 1.1)")
            stdscr.addstr(row + 3, 2, "Enter 0 to return: ")
            stdscr.refresh()
            
            # Get input
            choice = self._get_input(stdscr, "")
            if choice == "0":
                break
                
            try:
                if "." in choice:  # Toggle model
                    provider_num, model_num = map(int, choice.split("."))
                    if 1 <= provider_num <= len(providers):
                        provider = list(providers.keys())[provider_num - 1]
                        settings = providers[provider]
                        
                        if 'models' in settings and 1 <= model_num <= len(settings['models']):
                            model = settings['models'][model_num - 1]
                            active_models = settings.get('active_models', settings['models'][:])
                            
                            if model in active_models:
                                active_models.remove(model)
                            else:
                                active_models.append(model)
                                
                            settings['active_models'] = active_models
                            
                            # Ensure at least one model is active
                            if not active_models:
                                settings['active'] = False
                            elif not settings['active']:
                                settings['active'] = True
                else:  # Toggle provider
                    provider_num = int(choice)
                    if 1 <= provider_num <= len(providers):
                        provider = list(providers.keys())[provider_num - 1]
                        settings = providers[provider]
                        
                        # Toggle provider status
                        new_status = not settings.get('active', False)
                        settings['active'] = new_status
                        
                        # If enabling provider, ensure at least one model is active
                        if new_status and 'models' in settings:
                            if not settings.get('active_models'):
                                settings['active_models'] = settings['models'][:1]  # Enable first model
            except (ValueError, IndexError):
                pass

    def _edit_settings_menu(self, stdscr):
        """Menu for editing provider settings."""
        while True:
            stdscr.clear()
            providers = self.config['llm_providers']
            
            # Show providers
            stdscr.addstr(0, 2, "Edit Provider Settings", curses.A_BOLD)
            for i, name in enumerate(providers.keys(), 1):
                stdscr.addstr(i + 1, 2, f"{i}. {name.title()}")
            
            stdscr.addstr(len(providers) + 3, 2, "Enter provider number (0 to return): ")
            stdscr.refresh()
            
            try:
                choice = int(chr(stdscr.getch()))
                if choice == 0:
                    break
                if 1 <= choice <= len(providers):
                    provider = list(providers.keys())[choice - 1]
                    self._edit_provider(stdscr, provider)
            except ValueError:
                pass

    def _edit_provider(self, stdscr, provider: str):
        """Edit settings for a specific provider."""
        settings = self.config['llm_providers'][provider]
        
        while True:
            stdscr.clear()
            stdscr.addstr(0, 2, f"Edit {provider.title()} Settings", curses.A_BOLD)
            
            # Show current settings
            for i, (key, value) in enumerate(settings.items(), 1):
                stdscr.addstr(i + 1, 2, f"{i}. {key}: {value}")
            
            stdscr.addstr(len(settings) + 3, 2, "Enter setting number (0 to return): ")
            stdscr.refresh()
            
            try:
                choice = int(chr(stdscr.getch()))
                if choice == 0:
                    break
                if 1 <= choice <= len(settings):
                    key = list(settings.keys())[choice - 1]
                    new_value = self._get_input(stdscr, f"Enter new value for {key}: ")
                    
                    # Convert value type
                    old_value = settings[key]
                    if isinstance(old_value, bool):
                        settings[key] = new_value.lower() in ('true', 'yes', '1')
                    elif isinstance(old_value, int):
                        settings[key] = int(new_value)
                    elif isinstance(old_value, list):
                        settings[key] = [x.strip() for x in new_value.split(',')]
                    else:
                        settings[key] = new_value
            except ValueError:
                pass

    def _get_input(self, stdscr, prompt: str) -> str:
        """Get user input with a prompt."""
        height, width = stdscr.getmaxyx()
        input_win = curses.newwin(1, width - len(prompt) - 4, height - 2, len(prompt) + 2)
        textbox = textpad.Textbox(input_win)
        
        stdscr.addstr(height - 2, 2, prompt)
        stdscr.refresh()
        
        return textbox.edit().strip()

    def _test_connections(self, stdscr):
        """Test connections to enabled providers."""
        stdscr.clear()
        stdscr.addstr(0, 2, "Testing Provider Connections", curses.A_BOLD)
        row = 2
        
        for name, settings in self.config['llm_providers'].items():
            if settings.get('active'):
                stdscr.addstr(row, 2, f"Testing {name}... ")
                stdscr.refresh()
                
                try:
                    # Import provider dynamically
                    from llm_providers import LLMProviderFactory
                    provider = LLMProviderFactory.create_provider(name, settings)
                    
                    if provider and provider.is_available():
                        stdscr.addstr("Connected", curses.color_pair(2))
                    else:
                        stdscr.addstr("Failed", curses.color_pair(3))
                except Exception as e:
                    stdscr.addstr(f"Error: {e}", curses.color_pair(3))
                
                row += 1
        
        stdscr.addstr(row + 1, 2, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()

if __name__ == '__main__':
    # Run settings UI
    settings = ProviderSettings()
    curses.wrapper(settings.show_settings_ui)
