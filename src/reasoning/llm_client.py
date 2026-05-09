"""
LLM Client for Groq Integration

Implements Groq API client with OpenAI-compatible interface
for mutual fund RAG system generation.
"""

import os
import asyncio
from typing import Dict, List, Optional

import httpx

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GroqClient:
    """Groq LLM client with OpenAI-compatible interface."""
    
    def __init__(self, api_key: str, model: str = "llama3-70b-8192"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        
        # Default parameters for mutual fund responses
        self.default_temperature = 0.1
        self.default_max_tokens = 500
    
    async def chat_completion(
        self,
        messages: List[Dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict:
        """
        Create chat completion using Groq API.
        
        Args:
            messages: List of message dictionaries
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary with content and metadata
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
                **kwargs
            }
            
            logger.info(
                "Making Groq API call",
                model=self.model,
                messages_count=len(messages),
                temperature=payload.get("temperature"),
                max_tokens=payload.get("max_tokens")
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    logger.info(
                        "Groq API call successful",
                        model=self.model,
                        usage=result.get("usage", {}),
                        response_tokens=len(result.get("choices", [{}])[0].get("message", {}).get("content", ""))
                    )
                    
                    return {
                        "success": True,
                        "content": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                        "usage": result.get("usage", {}),
                        "model": result.get("model", self.model),
                        "finish_reason": result.get("choices", [{}])[0].get("finish_reason", "unknown")
                    }
                else:
                    error_text = response.text
                    logger.error(
                        "Groq API call failed",
                        status_code=response.status_code,
                        error=error_text
                    )
                    return {
                        "success": False,
                        "error": f"API Error ({response.status_code}): {error_text}"
                    }
                    
        except Exception as e:
            logger.error(
                "Groq API call exception",
                model=self.model,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"Exception: {str(e)}"
            }
    
    def is_available(self) -> bool:
        """Check if Groq client is properly configured."""
        return bool(self.api_key and self.model)
    
    def get_model_info(self) -> Dict:
        """Get information about the current model."""
        return {
            "provider": "Groq",
            "model": self.model,
            "api_base": self.base_url,
            "temperature": self.default_temperature,
            "max_tokens": self.default_max_tokens
        }


def create_groq_client() -> Optional[GroqClient]:
    """Create Groq client from environment variables."""
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not found in environment")
            return None
        
        model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        
        client = GroqClient(api_key=api_key, model=model)
        
        logger.info(
            "Groq client created",
            model=model,
            has_api_key=bool(api_key)
        )
        
        return client
        
    except Exception as e:
        logger.error(
            "Failed to create Groq client",
            error=str(e)
        )
        return None
