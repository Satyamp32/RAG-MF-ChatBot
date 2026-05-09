"""
Reasoning Orchestrator

Implements prompt orchestration, context injection, and response generation
with Groq LLM integration and guardrails enforcement.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from reasoning.llm_client import create_groq_client
from reasoning.guardrails import Guardrails
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReasoningOrchestrator:
    """Orchestrates LLM generation with context and guardrails."""
    
    def __init__(self, use_groq: Optional[str] = "auto"):
        self.use_groq = use_groq
        self.llm_client = None
        self.guardrails = Guardrails()
        
        # Initialize LLM client
        self._initialize_llm_client()
    
    def _initialize_llm_client(self) -> None:
        """Initialize LLM client based on configuration."""
        try:
            # Determine if Groq should be used
            use_groq = self.use_groq
            
            if use_groq == "auto":
                use_groq = os.getenv("GROQ_API_KEY") is not None
            
            if use_groq:
                self.llm_client = create_groq_client()
                if not self.llm_client:
                    logger.warning("Groq client initialization failed, falling back to extractive")
                    self.use_groq = False
                else:
                    logger.info("Groq LLM client initialized successfully")
            else:
                self.llm_client = None
                logger.info("Using extractive-only mode (no LLM)")
                
        except Exception as e:
            logger.error(
                "LLM client initialization failed",
                use_groq=self.use_groq,
                error=str(e)
            )
            self.llm_client = None
    
    async def generate_response(
        self,
        query: str,
        retrieved_chunks: List[Dict],
        query_type: str = "general"
    ) -> Dict:
        """
        Generate response using LLM or extractive synthesis.
        
        Args:
            query: Original user query
            retrieved_chunks: Retrieved chunks from Phase 2
            query_type: Type of query for prompt optimization
            
        Returns:
            Generated response with metadata
        """
        logger.info(
            "Starting response generation",
            query=query[:100] + "..." if len(query) > 100 else query,
            chunks_count=len(retrieved_chunks),
            query_type=query_type,
            use_groq=self.use_groq
        )
        
        try:
            # Prepare context from retrieved chunks
            context = self._prepare_context(retrieved_chunks)
            
            # Generate response
            if self.llm_client and self.use_groq:
                response = await self._generate_llm_response(query, context, query_type)
            else:
                response = await self._generate_extractive_response(query, retrieved_chunks)
            
            # Apply guardrails
            validated_response = self.guardrails.sanitize_response(response, context)
            
            # Add source attribution and URL policy
            if validated_response.get('success') and validated_response.get('response'):
                validated_response['response'] = self._add_source_attribution(
                    validated_response['response'],
                    retrieved_chunks
                )
            
            # Add final metadata
            validated_response['metadata'] = {
                'query': query,
                'chunks_used': len(retrieved_chunks),
                'query_type': query_type,
                'generation_method': 'groq' if self.use_groq else 'extractive',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'confidence': validated_response.get('confidence', 0.0),
                'source_url': self._get_source_url(retrieved_chunks) if retrieved_chunks else None,
                'last_updated': self._get_last_updated_date()
            }
            
            logger.info(
                "Response generation completed",
                success=validated_response.get('success', False),
                method=validated_response['metadata']['generation_method'],
                confidence=validated_response.get('confidence', 0.0)
            )
            
            return validated_response
            
        except Exception as e:
            logger.error(
                "Response generation failed",
                query=query[:50],
                error=str(e)
            )
            return {
                'success': False,
                'reason': f'Generation failed: {str(e)}',
                'response': None,
                'metadata': {
                    'query': query,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
    
    def _prepare_context(self, chunks: List[Dict]) -> str:
        """Prepare context from retrieved chunks."""
        if not chunks:
            return "No relevant information found in the retrieved documents."
        
        context_parts = []
        
        for i, chunk in enumerate(chunks[:5]):  # Use top 5 chunks
            chunk_text = chunk.get('text', '')
            scheme_id = chunk.get('scheme_id', 'unknown')
            section = chunk.get('section', 'unknown')
            score = chunk.get('score', 0.0)
            confidence = chunk.get('confidence', 0.0)
            
            context_parts.append(
                f"[Chunk {i+1}]\n"
                f"Scheme: {scheme_id}\n"
                f"Section: {section}\n"
                f"Score: {score:.3f}\n"
                f"Confidence: {confidence:.2f}\n"
                f"Content: {chunk_text}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    async def _generate_llm_response(
        self,
        query: str,
        context: str,
        query_type: str
    ) -> Dict:
        """Generate response using Groq LLM."""
        try:
            # Create system prompt based on query type
            system_prompt = self._create_system_prompt(query_type)
            
            # Create user prompt with context
            user_prompt = self._create_user_prompt(query, context)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Generate response
            response = await self.llm_client.chat_completion(
                messages=messages,
                temperature=0.1,  # Low temperature for factual responses
                max_tokens=500
            )
            
            if response['success']:
                content = response['content']
                
                # Extract confidence from response
                confidence = self._extract_confidence_from_response(content)
                
                return {
                    'success': True,
                    'content': content,
                    'confidence': confidence,
                    'method': 'groq'
                }
            else:
                return {
                    'success': False,
                    'reason': response.get('error', 'Unknown error'),
                    'content': None,
                    'method': 'groq'
                }
                
        except Exception as e:
            logger.error(
                "LLM response generation failed",
                query=query[:50],
                error=str(e)
            )
            return {
                'success': False,
                'reason': f'LLM error: {str(e)}',
                'content': None,
                'method': 'groq'
            }
    
    async def _generate_extractive_response(
        self,
        query: str,
        chunks: List[Dict]
    ) -> Dict:
        """Generate extractive response from top chunk."""
        try:
            if not chunks:
                return {
                    'success': False,
                    'reason': 'No chunks available',
                    'content': None,
                    'method': 'extractive'
                }
            
            # Use top chunk for extractive response
            top_chunk = chunks[0]
            chunk_text = top_chunk.get('text', '')
            
            # Extract key information (first 2-3 sentences)
            sentences = self._split_sentences(chunk_text)
            relevant_sentences = sentences[:3]  # Max 3 sentences
            
            content = ' '.join(relevant_sentences)
            
            # Add source information
            scheme_id = top_chunk.get('scheme_id', '')
            section = top_chunk.get('section', '')
            
            # Create extractive response with source
            response_content = f"{content}\n\nSource: {scheme_id} - {section}"
            
            return {
                'success': True,
                'content': response_content,
                'confidence': 0.8,  # High confidence for extractive
                'method': 'extractive',
                'source_chunk': top_chunk
            }
            
        except Exception as e:
            logger.error(
                "Extractive response generation failed",
                query=query[:50],
                error=str(e)
            )
            return {
                'success': False,
                'reason': f'Extractive error: {str(e)}',
                'content': None,
                'method': 'extractive'
            }
    
    def _create_system_prompt(self, query_type: str) -> str:
        """Create system prompt based on query type."""
        base_prompt = """You are a helpful assistant that provides factual information about mutual funds in India. 

Your role is to:
1. Answer questions based ONLY on the provided context
2. Be accurate and concise
3. Do not provide financial advice or recommendations
4. Do not hallucinate information not in the context
5. Keep responses under 3 sentences when possible
6. If information is unavailable, explicitly state so

Context will contain mutual fund information from official sources."""
        
        # Add query-type specific instructions
        if query_type == 'numerical_heavy':
            base_prompt += "\n\nFocus on providing accurate numerical data (percentages, amounts, dates)."
        elif query_type == 'section_specific':
            base_prompt += "\n\nFocus on the specific section mentioned in the query."
        elif query_type == 'semantic':
            base_prompt += "\n\nProvide comprehensive but concise answers based on the context."
        
        return base_prompt
    
    def _create_user_prompt(self, query: str, context: str) -> str:
        """Create user prompt with context."""
        return f"""Query: {query}

Context:
{context}

Based on the above context, please answer the query accurately and concisely. If the information is not available in the context, please state that clearly."""
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_confidence_from_response(self, response: str) -> float:
        """Extract confidence from LLM response."""
        # Look for confidence indicators in response
        response_lower = response.lower()
        
        # High confidence indicators
        high_confidence = [
            'based on the context',
            'according to the provided information',
            'the context shows',
            'as mentioned in the documents'
        ]
        
        # Low confidence indicators
        low_confidence = [
            'i am not certain',
            'i do not have enough information',
            'the context does not contain',
            'information is unavailable',
            'i cannot find'
        ]
        
        for indicator in high_confidence:
            if indicator in response_lower:
                return 0.8
        
        for indicator in low_confidence:
            if indicator in response_lower:
                return 0.2
        
        # Default confidence
        return 0.6
    
    def _add_source_attribution(self, response: str, chunks: List[Dict]) -> str:
        """Add source attribution and URL policy enforcement."""
        if not chunks:
            return response
        
        # Get top chunk for source
        top_chunk = chunks[0]
        scheme_id = top_chunk.get('scheme_id', '')
        section = top_chunk.get('section', '')
        
        # Get source URL
        source_url = self._get_source_url(chunks)
        
        # Format response with source attribution
        if source_url:
            attributed_response = f"{response}\n\nSource: {source_url}"
        else:
            attributed_response = f"{response}\n\nSource: {scheme_id} - {section}"
        
        # Add last updated date
        last_updated = self._get_last_updated_date()
        if last_updated:
            attributed_response += f"\nLast updated from sources: {last_updated}"
        
        return attributed_response
    
    def _get_source_url(self, chunks: List[Dict]) -> Optional[str]:
        """Get whitelisted source URL from chunks."""
        if not chunks:
            return None
        
        # Try to get URL from top chunk metadata
        top_chunk = chunks[0]
        metadata = top_chunk.get('metadata', {})
        
        # Check for source URL in metadata
        if 'source_url' in metadata:
            return metadata['source_url']
        
        # Check for scheme URL from sources.yaml
        try:
            from src.utils.config import config_manager
            sources = config_manager.load_sources()
            scheme_id = top_chunk.get('scheme_id', '')
            
            for scheme in sources.get('schemes', []):
                if scheme.get('id') == scheme_id:
                    for source in scheme.get('sources', []):
                        url = source.get('url', '')
                        if url and self.guardrails._is_whitelisted_url(url):
                            return url
        except Exception as e:
            logger.error("Failed to get source URL", error=str(e))
        
        return None
    
    def _get_last_updated_date(self) -> Optional[str]:
        """Get last updated date from sources."""
        try:
            from src.utils.config import config_manager
            sources = config_manager.load_sources()
            return sources.get('last_updated', '2024-01-01')
        except Exception as e:
            logger.error("Failed to get last updated date", error=str(e))
            return None
