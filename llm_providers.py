#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import shutil
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import subprocess
import google.generativeai as genai

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self):
        self.initialized = False
        
    @abstractmethod
    def generate_code(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate code from prompt."""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass
        
    def initialize(self) -> bool:
        """Initialize the provider if needed."""
        if not self.initialized:
            self.initialized = self._initialize()
        return self.initialized
        
    def _initialize(self) -> bool:
        """Provider-specific initialization."""
        return True

class LocalLLMProvider(LLMProvider):
    """Provider for local LLM server."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.url = config['url']
        self.models = config['models']
        self.timeout = config.get('timeout', 30)

    def generate_code(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate code using local LLM."""
        if not self.initialize():
            return None
            
        try:
            response = requests.post(
                f"{self.url}/chat/completions",
                json={
                    "model": self.models[0],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get('temperature', 0.7),
                    "max_tokens": kwargs.get('max_tokens', 2000)
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Local LLM error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if local LLM server is running."""
        try:
            requests.get(self.url, timeout=2)
            return True
        except:
            return False

class VSCodeLLMProvider(LLMProvider):
    """Provider for VSCode Copilot."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.extension_id = config['extension_id']
        self.timeout = config.get('timeout', 10)
        self._extension_path = None
        self._code_path = None
        self.temp_dir = os.path.join(os.getcwd(), '.vscode_temp')

    def _initialize(self) -> bool:
        """Initialize VSCode paths and workspace."""
        if sys.platform == 'win32':
            vscode_paths = [
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\Microsoft VS Code'),
                os.path.expandvars(r'%ProgramFiles%\Microsoft VS Code'),
                os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft VS Code')
            ]
            extensions_path = os.path.expandvars(
                r'%USERPROFILE%\.vscode\extensions'
            )
        else:
            vscode_paths = [
                '/usr/share/code',
                '/usr/local/share/code',
                os.path.expanduser('~/.local/share/code')
            ]
            extensions_path = os.path.expanduser('~/.vscode/extensions')

        # Find VSCode installation
        for path in vscode_paths:
            code_exe = os.path.join(path, 'code.exe' if sys.platform == 'win32' else 'code')
            if os.path.isfile(code_exe):
                self._code_path = code_exe
                break

        # Find Copilot extension
        if os.path.isdir(extensions_path):
            for ext in os.listdir(extensions_path):
                if ext.lower().startswith(self.extension_id.lower()):
                    self._extension_path = os.path.join(extensions_path, ext)
                    break
                    
        # Create temp workspace if needed
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir, exist_ok=True)
            
        return bool(self._code_path and self._extension_path)

    def generate_code(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate code using VSCode Copilot."""
        if not self.initialize():
            return None
            
        try:
            # Create temporary files
            prompt_file = os.path.join(self.temp_dir, 'prompt.txt')
            response_file = os.path.join(self.temp_dir, 'response.txt')
            
            # Write prompt
            with open(prompt_file, 'w') as f:
                f.write(f"// {prompt}\n")
            
            # Launch VSCode with extension
            process = subprocess.Popen([
                self._code_path,
                '--disable-workspace-trust',
                '--disable-extensions',
                f'--install-extension={self._extension_path}',
                self.temp_dir
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for Copilot to generate
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if os.path.exists(response_file):
                    with open(response_file, 'r') as f:
                        content = f.read()
                    if content.strip():
                        return content
                time.sleep(0.5)
                
            process.terminate()
            return None
            
        except Exception as e:
            print(f"VSCode Copilot error: {e}")
            return None
            
    def is_available(self) -> bool:
        """Check if Copilot is available."""
        return self.initialize()
        
    def __del__(self):
        """Cleanup temporary files."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass

class GeminiProvider(LLMProvider):
    """Provider for Google's Gemini."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.api_key = config['api_key']
        self.model = config['model']
        self.timeout = config.get('timeout', 30)

    def _initialize(self) -> bool:
        """Initialize Gemini API."""
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                return True
            except Exception as e:
                print(f"Gemini initialization error: {e}")
        return False

    def generate_code(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate code using Gemini."""
        if not self.initialize():
            return None
            
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": kwargs.get('temperature', 0.7),
                    "max_output_tokens": kwargs.get('max_tokens', 2000),
                    "top_p": 1,
                    "top_k": 40
                }
            )
            return response.text
        except Exception as e:
            print(f"Gemini error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Gemini API is accessible."""
        return bool(self.api_key)

class OpenRouteProvider(LLMProvider):
    """Provider for OpenRoute API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.api_key = config['api_key']
        self.base_url = config.get('base_url', 'https://openrouter.ai/api/v1')
        self.model = config.get('model', 'openrouter/auto')
        self.timeout = config.get('timeout', 30)
    
    def generate_code(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate code using OpenRoute API."""
        if not self.initialize():
            print("OpenRoute initialization failed")
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://anjdev.terminal",  # Required by OpenRouter
                "X-Title": "ANJ DEV Terminal"  # Helps with billing
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get('temperature', 0.7),
                "max_tokens": kwargs.get('max_tokens', 2000)
            }
            
            print(f"OpenRoute request: {self.base_url}/chat/completions")
            print(f"OpenRoute model: {self.model}")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # Print response status and headers for debugging
            print(f"OpenRoute response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"OpenRoute error response: {response.text}")
                return None
                
            response_json = response.json()
            print(f"OpenRoute response JSON: {response_json}")
            
            if 'choices' not in response_json or not response_json['choices']:
                print("No choices in OpenRoute response")
                return None
                
            if 'message' not in response_json['choices'][0]:
                print("No message in OpenRoute response choice")
                return None
                
            if 'content' not in response_json['choices'][0]['message']:
                print("No content in OpenRoute response message")
                return None
                
            content = response_json['choices'][0]['message']['content']
            
            # Log token usage if available
            if 'usage' in response_json:
                usage = response_json['usage']
                print(f"OpenRoute tokens - Prompt: {usage.get('prompt_tokens', 0)}, "
                      f"Completion: {usage.get('completion_tokens', 0)}, "
                      f"Total: {usage.get('total_tokens', 0)}")
                
            return content
            
        except requests.exceptions.RequestException as e:
            print(f"OpenRoute request error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"OpenRoute JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"OpenRoute unexpected error: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if OpenRoute API is accessible."""
        return bool(self.api_key)

class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    _instances = {}
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> Optional[LLMProvider]:
        """Create or return cached provider instance."""
        if provider_type not in cls._instances:
            providers = {
                'local': LocalLLMProvider,
                'vscode': VSCodeLLMProvider,
                'gemini': GeminiProvider,
                'openroute': OpenRouteProvider
            }
            
            provider_class = providers.get(provider_type)
            if provider_class:
                cls._instances[provider_type] = provider_class(config)
                
        return cls._instances.get(provider_type)

    @classmethod
    def get_available_providers(cls, config: Dict[str, Any]) -> Dict[str, LLMProvider]:
        """Get all configured and available providers."""
        available = {}
        
        for provider_name, provider_config in config.get('llm_providers', {}).items():
            if provider_config.get('active'):
                provider = cls.create_provider(provider_name, provider_config)
                if provider and provider.is_available():
                    available[provider_name] = provider
                    
        return available

    @classmethod
    def clear_cache(cls):
        """Clear provider instance cache."""
        cls._instances.clear()
