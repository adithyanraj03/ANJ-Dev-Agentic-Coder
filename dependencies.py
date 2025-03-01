#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path
from typing import List, Dict, Set
from packaging.version import parse as parse_version
from packaging.requirements import Requirement

class DependencyManager:
    """Manage Python package dependencies."""

    @staticmethod
    def parse_requirement(req_str: str) -> Dict[str, str]:
        """Parse a requirement string into package name and version."""
        try:
            req = Requirement(req_str)
            name = req.name
            specs = req.specifier
            return {"name": name, "version": str(specs) if specs else ""}
        except Exception:
            # Simple fallback parsing for basic requirements
            parts = req_str.split(">=")
            if len(parts) == 2:
                return {"name": parts[0].strip(), "version": f">={parts[1].strip()}"}
            return {"name": req_str.strip(), "version": ""}

    @staticmethod
    def merge_requirements(base_reqs: List[str], new_reqs: List[str]) -> List[str]:
        """Merge requirement lists, keeping highest version constraints."""
        req_dict: Dict[str, str] = {}
        
        # Process all requirements
        for req_list in [base_reqs, new_reqs]:
            for req_str in req_list:
                req = DependencyManager.parse_requirement(req_str)
                name, version = req["name"], req["version"]
                
                if name not in req_dict:
                    req_dict[name] = version
                else:
                    # If we have conflicting versions, keep the higher one
                    current_ver = req_dict[name]
                    if version and current_ver:
                        # Extract version numbers
                        current_num = re.search(r'[\d.]+', current_ver)
                        new_num = re.search(r'[\d.]+', version)
                        
                        if current_num and new_num:
                            if parse_version(new_num.group()) > parse_version(current_num.group()):
                                req_dict[name] = version
                    elif version:  # Current has no version constraint
                        req_dict[name] = version

        # Convert back to requirement strings
        return [
            f"{name}{version}" if version else name
            for name, version in sorted(req_dict.items())
        ]

    @staticmethod
    def load_base_requirements(file_path: str = "requirements.txt") -> List[str]:
        """Load base requirements from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [
                    line.strip() 
                    for line in f 
                    if line.strip() and not line.startswith('#')
                ]
        except FileNotFoundError:
            return []

    @staticmethod
    def save_requirements(
        requirements: List[str],
        file_path: str = "requirements.txt"
    ) -> None:
        """Save requirements to file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Generated requirements file\n")
            for req in requirements:
                f.write(f"{req}\n")

    @staticmethod
    def detect_provider_dependencies() -> Dict[str, List[str]]:
        """Detect required dependencies for different LLM providers."""
        provider_deps = {
            "base": [
                "colorama>=0.4.6",
                "cursor>=1.3.5",
                "pyfiglet>=0.8.post1",
                "requests>=2.31.0",
                "packaging>=23.0"
            ],
            "vscode": [
                # VSCode extension dependencies are handled by VSCode
            ],
            "gemini": [
                "google-generativeai>=0.3.0"
            ],
            "local": [
                "requests>=2.31.0"
            ]
        }
        return provider_deps

    @staticmethod
    def update_provider_dependencies(config: Dict) -> None:
        """Update requirements based on active providers."""
        deps = DependencyManager.detect_provider_dependencies()
        requirements = deps["base"].copy()  # Start with base dependencies
        
        # Add dependencies for active providers
        for provider, settings in config.get('llm_providers', {}).items():
            if settings.get('active', False) and provider in deps:
                requirements.extend(deps[provider])
        
        # Merge with existing requirements
        base_reqs = DependencyManager.load_base_requirements()
        final_reqs = DependencyManager.merge_requirements(base_reqs, requirements)
        
        # Save updated requirements
        DependencyManager.save_requirements(final_reqs)

    @staticmethod
    def get_missing_dependencies() -> Set[str]:
        """Get list of missing required dependencies."""
        import pkg_resources
        missing = set()
        
        for req_str in DependencyManager.load_base_requirements():
            req = DependencyManager.parse_requirement(req_str)
            package = req["name"]
            
            try:
                pkg_resources.require(package)
            except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
                missing.add(package)
                
        return missing

    @staticmethod
    def install_dependencies(packages: Set[str], upgrade: bool = False) -> bool:
        """Install missing dependencies."""
        import subprocess
        import sys
        
        if not packages:
            return True
            
        try:
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                *(["-U"] if upgrade else []),
                *packages
            ]
            subprocess.check_call(cmd)
            return True
        except subprocess.CalledProcessError:
            return False

if __name__ == "__main__":
    # If run directly, update dependencies based on current config
    import json
    
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            config = json.load(f)
        DependencyManager.update_provider_dependencies(config)
        
        # Check and install missing dependencies
        missing = DependencyManager.get_missing_dependencies()
        if missing:
            print(f"Installing missing dependencies: {', '.join(missing)}")
            if DependencyManager.install_dependencies(missing):
                print("Dependencies installed successfully")
            else:
                print("Failed to install some dependencies")
    except Exception as e:
        print(f"Error updating dependencies: {e}")
