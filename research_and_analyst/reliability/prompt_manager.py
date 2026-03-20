"""
Prompt Versioning Manager — file-based prompt management with version control.

Stores prompts as versioned files, enabling:
- Rollback to previous versions
- A/B testing between prompt versions
- Audit trail of prompt changes
"""

import os
import hashlib
from typing import Dict, List, Optional

from research_and_analyst.logger import GLOBAL_LOGGER as log


class PromptManager:
    """
    Manages versioned prompt templates stored as files.

    Directory structure:
        prompts/
        ├── v1/
        │   ├── research.txt
        │   ├── decision.txt
        │   └── critic.txt
        └── v2/
            ├── research.txt
            └── decision.txt
    """

    def __init__(self, prompts_dir: str = "prompts", default_version: str = "v1"):
        self.prompts_dir = prompts_dir
        self.default_version = default_version
        self._cache: Dict[str, str] = {}

    def get(self, prompt_name: str, version: Optional[str] = None) -> str:
        """
        Load a prompt by name and version.

        Args:
            prompt_name: Prompt identifier (e.g., 'research', 'decision').
            version: Version string (e.g., 'v1', 'v2'). Defaults to default_version.

        Returns:
            Prompt text content.
        """
        ver = version or self.default_version
        cache_key = f"{ver}/{prompt_name}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        file_path = os.path.join(self.prompts_dir, ver, f"{prompt_name}.txt")

        if not os.path.exists(file_path):
            # Fallback to default version
            fallback_path = os.path.join(self.prompts_dir, self.default_version, f"{prompt_name}.txt")
            if os.path.exists(fallback_path):
                log.warning(
                    "Prompt version not found, falling back",
                    prompt=prompt_name,
                    requested=ver,
                    fallback=self.default_version,
                )
                file_path = fallback_path
            else:
                log.error("Prompt not found", prompt=prompt_name, version=ver)
                raise FileNotFoundError(f"Prompt '{prompt_name}' not found in version '{ver}'")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._cache[cache_key] = content
        log.info("Prompt loaded", prompt=prompt_name, version=ver, hash=self._hash(content)[:8])
        return content

    def list_versions(self) -> List[str]:
        """List all available prompt versions."""
        if not os.path.exists(self.prompts_dir):
            return []
        return sorted(
            d for d in os.listdir(self.prompts_dir)
            if os.path.isdir(os.path.join(self.prompts_dir, d))
        )

    def list_prompts(self, version: Optional[str] = None) -> List[str]:
        """List all prompts in a version."""
        ver = version or self.default_version
        ver_dir = os.path.join(self.prompts_dir, ver)
        if not os.path.exists(ver_dir):
            return []
        return sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(ver_dir)
            if f.endswith(".txt")
        )

    def get_with_metadata(self, prompt_name: str, version: Optional[str] = None) -> Dict:
        """Load prompt with metadata for audit trail."""
        ver = version or self.default_version
        content = self.get(prompt_name, ver)
        file_path = os.path.join(self.prompts_dir, ver, f"{prompt_name}.txt")

        return {
            "prompt_name": prompt_name,
            "version": ver,
            "content": content,
            "hash": self._hash(content),
            "file_path": file_path,
            "char_count": len(content),
        }

    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()
