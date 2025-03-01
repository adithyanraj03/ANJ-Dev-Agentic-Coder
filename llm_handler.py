#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import logging
import time
from typing import Dict, Any, Optional, Iterator, List, Tuple
from llm_providers import LLMProviderFactory
# Try to import log queue, but have a fallback mechanism
try:
    from queue_handler import log_queue
    HAS_LOG_QUEUE = True
except ImportError:
    HAS_LOG_QUEUE = False
    import logging
    logging.basicConfig(level=logging.INFO)

class LLMHandler:
    """Handles interactions with LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize handler."""
        self.config = config
        self.provider_factory = LLMProviderFactory()
        self.providers = self.provider_factory.get_available_providers(config)
        self.providers_order = ["local", "gemini", "vscode"]
        if HAS_LOG_QUEUE:
            self._log("LLM Handler initialized", "INFO")
        else:
            logging.info("LLM Handler initialized")
        
    def _log(self, message: str, level: str = 'INFO'):
        """Log message."""
        if HAS_LOG_QUEUE:
            log_queue.put({"message": message, "level": level})
        else:
            if level == "ERROR":
                logging.error(message)
            elif level == "WARNING":
                logging.warning(message)
            elif level == "DEBUG":
                logging.debug(message)
            else:
                logging.info(message)

    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from response."""
        # Remove markdown code block markers
        response = re.sub(r'```(?:json)?\s*\n', '', response)
        response = re.sub(r'\n\s*```', '', response)
        
        # Remove any leading/trailing whitespace
        response = response.strip()
        
        # Ensure it starts with { and ends with }
        if not response.startswith('{'):
            start_idx = response.find('{')
            if (start_idx != -1):
                response = response[start_idx:]
                
        if not response.endswith('}'):
            end_idx = response.rfind('}')
            if (end_idx != -1):
                response = response[:end_idx+1]
                
        # Fix common JSON formatting issues
        response = re.sub(r',\s*}', '}', response)  # Remove trailing commas
        response = re.sub(r',\s*]', ']', response)  # Remove trailing commas in arrays
        
        return response

    def _try_provider_with_models(self, provider_name: str, provider, prompt: str) -> Tuple[Optional[str], List[str]]:
        """Try a provider with all its available models."""
        errors = []
        provider_config = self.config['llm_providers'][provider_name]
        original_model = provider_config.get('model')
        models = provider_config.get('models', [original_model] if original_model else [])

        # Use active_models if available, otherwise use all models
        active_models = provider_config.get('active_models', models)
        
        for model in active_models:
            if not model or model not in models:  # Skip if model not in original models list
                continue
                
            try:
                self._log(f"Trying {provider_name} with model: {model}", "INFO")
                provider_config['model'] = model
                response = provider.generate_code(prompt)
                
                if response:
                    if "error" in str(response).lower():
                        self._log(f"Model {model} returned error response", "WARNING")
                        errors.append(f"{model}: {response}")
                        continue
                        
                    self._log(f"Got response from {model}", "SUCCESS")
                    
                    # For Gemini responses, try to clean up JSON
                    if provider_name == 'gemini' and '{' in response:
                        try:
                            # Try to parse as JSON first
                            json.loads(response)
                        except json.JSONDecodeError:
                            # If parsing fails, try to clean up the response
                            response = self._clean_json_response(response)
                            try:
                                # Verify the cleaned response is valid JSON
                                json.loads(response)
                            except json.JSONDecodeError as e:
                                self._log(f"Failed to clean JSON response: {e}", "ERROR")
                                continue
                                
                    # Handle LM Studio Server responses
                    if "[LM STUDIO SERVER]" in str(response):
                        try:
                            server_data = json.loads(response)
                            if "choices" in server_data:
                                message = server_data["choices"][0]["message"]
                                if "content" in message:
                                    response = message["content"]
                                    
                            # Log token usage
                            if "usage" in server_data:
                                usage = server_data["usage"]
                                self._log(
                                    f"Tokens - Prompt: {usage.get('prompt_tokens', 0)}, "
                                    f"Completion: {usage.get('completion_tokens', 0)}, "
                                    f"Total: {usage.get('total_tokens', 0)}",
                                    "INFO"
                                )
                        except json.JSONDecodeError:
                            # If not JSON, extract content between content markers
                            start = response.find('"content": "')
                            if start != -1:
                                start += len('"content": "')
                                end = response.find('"\n', start)
                                if end != -1:
                                    response = response[start:end]
                                    
                    # Log the actual response for debugging
                    self._log(f"Raw response:\n{response}", "DEBUG")
                    return response, errors
                    
            except Exception as e:
                self._log(f"Model {model} error: {e}", "ERROR")
                errors.append(f"{model}: {str(e)}")
                continue
                
        # Restore original model setting
        if original_model:
            provider_config['model'] = original_model
            
        return None, errors

    def execute_query(self, prompt: str, stdscr=None) -> str:
        """Execute a query to the LLM provider."""
        # First stop any running loading animations
        if hasattr(self, 'planner') and self.planner:
            if hasattr(self.planner, 'session_window') and self.planner.session_window:
                self.planner.session_window.is_loading = False
                self.planner.session_window.stop_loading()
                
        self._log("Executing query", "INFO")
        # Reset last response
        self._last_raw_response = ""
        self._last_parsed_response = {}
        
        # If planner is attached, ensure it has the screen
        if hasattr(self, 'planner'):
            self.planner.set_screen(stdscr)
            
        # For thread safety, create new loading context
        if hasattr(self, 'planner') and self.planner and hasattr(self.planner, 'session_window'):
            self.planner.session_window.is_loading = True
        
        # Try each provider in order
        for provider_name in self.providers_order:
            if not self.config.get("llm_providers", {}).get(provider_name, {}).get("active", False):
                continue
                
            # Get models for this provider
            models = self.config.get("llm_providers", {}).get(provider_name, {}).get("models", [])
            if not models and provider_name != "vscode":  # vscode doesn't need models
                continue
                
            # Try each model
            for model in (models or [None]):
                try:
                    self._log(f"Trying {provider_name} with model: {model}", "INFO")
                    
                    # Get appropriate provider function
                    response_text = None
                    if provider_name == "vscode":
                        response_text = self._query_vscode(prompt)
                    elif provider_name == "local":
                        response_text = self._query_local(prompt, model)
                    elif provider_name == "gemini":
                        response_text = self._query_gemini(prompt, model)
                    else:
                        continue
                        
                    # If we got a response, we're done
                    if response_text:
                        self._log(f"Got response from {model or provider_name}", "SUCCESS")
                        self._last_raw_response = response_text
                        
                        # Try parsing the JSON response with triple-quoted string handling
                        try:
                            self._last_parsed_response = self._parse_json_with_triple_quotes(response_text)
                            self._log(f"Parsed response: {self._last_parsed_response}", "DEBUG")
                        except json.JSONDecodeError as e:
                            self._log(f"JSON parsing error: {e}", "ERROR")
                            self._log(f"Response text:\n{response_text}", "DEBUG")
                            self._last_parsed_response = {}
                            
                        return response_text
                except Exception as e:
                    self._log(f"Error with {provider_name} ({model}): {e}", "ERROR")
                    continue
                    
        # If we get here, we couldn't get a response from any provider
        self._log("All providers failed", "ERROR")
        return ""

    def execute_query_stream(self, prompt: str) -> Iterator[str]:
        """Execute a query with streaming response."""
        # Reset last response
        self._last_raw_response = ""
        self._last_parsed_response = {}
        
        # Try each provider in order
        for provider_name in self.providers_order:
            if not self.config.get("llm_providers", {}).get(provider_name, {}).get("active", False):
                continue
                
            # Get models for this provider
            models = self.config.get("llm_providers", {}).get(provider_name, {}).get("models", [])
            if not models and provider_name != "vscode":
                continue
                
            # Try each model
            for model in (models or [None]):
                try:
                    logging.info(f"Trying {provider_name} streaming with model: {model}")
                    
                    # Get appropriate provider function
                    if provider_name == "local":
                        yield from self._query_local_stream(prompt, model)
                        return
                    elif provider_name == "gemini":
                        yield from self._query_gemini_stream(prompt, model)
                        return
                    else:
                        # If streaming isn't supported, fall back to non-streaming
                        response_text = ""
                        if provider_name == "vscode":
                            response_text = self._query_vscode(prompt)
                        
                        if response_text:
                            self._last_raw_response = response_text
                            yield response_text
                            return
                except Exception as e:
                    logging.error(f"Error with streaming {provider_name} ({model}): {e}")
                    continue
                    
        # If we get here, we couldn't get a response from any provider
        logging.error("All streaming providers failed")
        yield ""

    def _extract_code_blocks(self, response: str) -> Dict[str, str]:
        """Extract code blocks from LLM response.
        
        Handles various formats including triple-quoted strings that might
        confuse JSON parsers.
        """
        blocks = {}
        
        # Try to parse as JSON first
        try:
            data = json.loads(response)
            # If it's already a dictionary with files/code, return it
            if isinstance(data, dict) and 'files' in data:
                for filename, content in data['files'].items():
                    blocks[filename] = content
                return blocks
        except json.JSONDecodeError:
            pass
        
        # Look for code blocks in markdown format
        code_blocks = re.findall(r'```(?:\w+)?\s*([\s\S]*?)```', response)
        if code_blocks:
            for i, block in enumerate(code_blocks):
                # Try to determine filename from context
                filename_match = re.search(r'filename[=:]?\s*[\'"]?([^\'"]+)[\'"]?', response, re.IGNORECASE)
                if filename_match:
                    filename = filename_match.group(1)
                else:
                    # Default filename if none found
                    filename = f"file_{i+1}.txt"
                    
                    # Try to guess file extension from content
                    if "import pygame" in block:
                        filename = f"game_{i+1}.py"
                    elif "<html>" in block.lower():
                        filename = f"index_{i+1}.html"
                    elif "def " in block and "return" in block:
                        filename = f"script_{i+1}.py"
                    
                blocks[filename] = block
                
        # If we're dealing with a plan-style response
        plan_match = re.search(r'"steps"\s*:\s*\[\s*{([^}]+)}', response, re.DOTALL)
        if plan_match:
            step_data = plan_match.group(1)
            file_match = re.search(r'"file"\s*:\s*"([^"]+)"', step_data)
            content_match = re.search(r'"content"\s*:\s*"""([\s\S]*?)"""', step_data)
            
            if file_match and content_match:
                filename = file_match.group(1)
                content = content_match.group(1)
                blocks[filename] = content
        
        # If still no blocks found, try to extract from the entire text
        if not blocks:
            # For Python files
            if re.search(r'def\s+\w+\s*\(', response) and re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', response):
                blocks["script.py"] = response
                
        return blocks
        
    def _parse_json_with_triple_quotes(self, response: str) -> Dict[str, Any]:
        """Parse JSON that contains triple-quoted strings.
        
        This is a workaround for the issue where triple-quoted strings in JSON
        confuse the parser.
        """
        # First try standard parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Handle triple-quoted strings by temporarily replacing them
        placeholders = {}
        placeholder_pattern = "__TRIPLE_QUOTE_CONTENT_{}_PLACEHOLDER__"
        
        def replace_triple_quotes(match):
            content = match.group(1)
            placeholder = placeholder_pattern.format(len(placeholders))
            placeholders[placeholder] = content
            return f'"{placeholder}"'
        
        # Replace triple-quoted strings with placeholders
        modified_response = re.sub(r'"""([\s\S]*?)"""', replace_triple_quotes, response)
        
        try:
            result = json.loads(modified_response)
            
            # Restore placeholders with actual content
            def restore_placeholders(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, str) and v in placeholders:
                            obj[k] = placeholders[v]
                        else:
                            restore_placeholders(v)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, str) and item in placeholders:
                            obj[i] = placeholders[item]
                        else:
                            restore_placeholders(item)
            
            restore_placeholders(result)
            return result
        except json.JSONDecodeError:
            # If still failing, return empty dict
            return {}

    def _query_local(self, prompt: str, model: str) -> str:
        """Query a local LLM API."""
        import requests
        
        # Get the base URL and timeout
        url = self.config.get("llm_providers", {}).get("local", {}).get("url", "http://localhost:1234/v1")
        timeout = self.config.get("llm_providers", {}).get("local", {}).get("timeout", 30)
        
        # Build the request
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        try:
            # Make the request
            response = requests.post(
                f"{url}/chat/completions",
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            # Parse the response
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                logging.debug(f"Raw response:\n{response_text}")
                logging.debug("-" * 80)
                logging.debug(response_text)
                logging.debug("-" * 80)
                
                return response_text
            else:
                logging.error(f"Error from local LLM: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            logging.error(f"Exception in _query_local: {e}")
            return ""

    def _query_local_stream(self, prompt: str, model: str) -> Iterator[str]:
        """Query a local LLM API with streaming."""
        import requests
        
        # Get the base URL and timeout
        url = self.config.get("llm_providers", {}).get("local", {}).get("url", "http://localhost:1234/v1")
        timeout = self.config.get("llm_providers", {}).get("local", {}).get("timeout", 30)
        
        # Build the request
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 30000,
            "stream": True
        }
        
        try:
            # Make the streaming request
            response = requests.post(
                f"{url}/chat/completions",
                headers=headers,
                json=data,
                timeout=timeout,
                stream=True
            )
            
            # Process the streaming response
            if response.status_code == 200:
                complete_response = ""
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            line = line[6:]  # Remove 'data: ' prefix
                            
                            if line == '[DONE]':
                                break
                                
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                
                                if content:
                                    complete_response += content
                                    yield content
                            except json.JSONDecodeError:
                                continue
                
                # Store the complete response
                self._last_raw_response = complete_response
            else:
                logging.error(f"Error from local LLM stream: {response.status_code} - {response.text}")
                yield ""
        except Exception as e:
            logging.error(f"Exception in _query_local_stream: {e}")
            yield ""

    def _query_gemini(self, prompt: str, model: str) -> str:
        """Query the Gemini API."""
        # Check if API key is set
        api_key = self.config.get("llm_providers", {}).get("gemini", {}).get("api_key", "")
        if not api_key:
            logging.error("Gemini API key not set")
            return ""
            
        try:
            import google.generativeai as genai
            
            # Configure the API
            genai.configure(api_key=api_key)
            
            # Set up the model
            generation_config = {
                "temperature": 0.7,
                "max_output_tokens": 4096,
            }
            
            # Initialize the model
            model_name = model or self.config.get("llm_providers", {}).get("gemini", {}).get("model", "gemini-pro")
            model = genai.GenerativeModel(model_name=model_name)
            
            # Generate content
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract and return the text
            response_text = response.text
            
            logging.debug(f"Raw Gemini response:\n{response_text}")
            return response_text
            
        except Exception as e:
            logging.error(f"Error with Gemini API: {e}")
            return ""

    def _query_gemini_stream(self, prompt: str, model: str) -> Iterator[str]:
        """Query the Gemini API with streaming."""
        # Check if API key is set
        api_key = self.config.get("llm_providers", {}).get("gemini", {}).get("api_key", "")
        if not api_key:
            logging.error("Gemini API key not set")
            yield ""
            return
            
        try:
            import google.generativeai as genai
            
            # Configure the API
            genai.configure(api_key=api_key)
            
            # Set up the model
            generation_config = {
                "temperature": 0.7,
                "max_output_tokens": 4096,
            }
            
            # Initialize the model
            model_name = model or self.config.get("llm_providers", {}).get("gemini", {}).get("model", "gemini-pro")
            model = genai.GenerativeModel(model_name=model_name)
            
            # Generate content with streaming
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            # Process the streaming response
            complete_response = ""
            for chunk in response:
                if chunk.text:
                    complete_response += chunk.text
                    yield chunk.text
                    
            # Store the complete response
            self._last_raw_response = complete_response
            
        except Exception as e:
            logging.error(f"Error with Gemini API streaming: {e}")
            yield ""

    def _query_vscode(self, prompt: str) -> str:
        """Query VSCode's Copilot extension."""
        try:
            from vscode_extension_api import VSCodeExtension
            
            # Get the extension ID
            extension_id = self.config.get("llm_providers", {}).get("vscode", {}).get("extension_id", "GitHub.copilot")
            
            # Initialize the extension
            extension = VSCodeExtension(extension_id)
            
            # Query the extension
            response_text = extension.query(prompt)
            
            logging.debug(f"Raw VSCode response:\n{response_text}")
            return response_text
            
        except ImportError:
            logging.error("VSCode extension API not available")
            return ""
        except Exception as e:
            logging.error(f"Error with VSCode extension: {e}")
            return ""
