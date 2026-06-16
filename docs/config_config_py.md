# `config/config.py` — Line-by-Line Explanation

**File:** `config/config.py`  
**Role:** Centralised configuration manager using `pydantic-settings`. Loads environment variables from a `.env` file with robust type conversion and validation.

---

## Imports and Paths (Lines 5–12)

```python
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
```

- **`lru_cache`**: Caches the result of a function. Used later to make config loading a singleton.
- **`BaseSettings`**: A Pydantic class designed to read variables from the environment and validate them.
- **`_PROJECT_ROOT`**: Computes the absolute path to the main folder by going up two directories from this file's location. Finds the `.env` file reliably regardless of where the user runs the script from.

---

## The Settings Class (Lines 15–47)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_temperature: float = Field(default=0.2)
    groq_max_tokens: int = Field(default=4096)
```

- **`SettingsConfigDict`**: Tells Pydantic to read from the `.env` file path. `extra="ignore"` means if `.env` has variables not listed here, don't crash.
- **`Field(default=...)`**: Provides default values. Pydantic automatically casts types—if `GROQ_TEMPERATURE="0.5"` is in the `.env` file as a string, Pydantic parses it into a float.

---

## Computed Properties (Lines 49–55)

```python
    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key != "your_groq_api_key_here")

    @property
    def has_tavily_key(self) -> bool:
        return bool(self.tavily_api_key and self.tavily_api_key != "your_tavily_api_key_here")
```

- Helper properties to let the application know if valid API keys have actually been set, avoiding crashes deeper in the code when the user just left the placeholder string in `.env.example`.

---

## Singleton Getter (Lines 58–61)

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
```

- **`@lru_cache(maxsize=1)`**: The first time `get_settings()` is called, it instantiates `Settings` (which reads the disk and parses `.env`). Every subsequent call throughout the app returns the exact same object instantly. This ensures config loading is highly performant.
