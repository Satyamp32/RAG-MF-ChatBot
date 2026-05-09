"""
Phase 1.4 - Chunking Strategy

Implements section-aware chunking with size optimization, metadata preservation,
and semantic boundary detection for mutual fund data.
"""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ContentChunker:
    """Section-aware content chunker with size optimization."""
    
    def __init__(self, soft_cap: int = 250, hard_cap: int = 400, overlap: int = 30):
        self.soft_cap = soft_cap
        self.hard_cap = hard_cap
        self.overlap = overlap
        
        # Token estimation (rough: 1 token ≈ 4 characters)
        self.soft_cap_tokens = soft_cap
        self.hard_cap_tokens = hard_cap
        self.overlap_tokens = overlap
    
    def chunk_document(self, cleaned_document: Dict, scheme_id: str) -> List[Dict]:
        """
        Chunk cleaned document into section-aware retrieval units.
        
        Args:
            cleaned_document: Cleaned document from Phase 1.3
            scheme_id: Scheme identifier
            
        Returns:
            List of chunk dictionaries with metadata
        """
        logger.info(
            "Starting document chunking",
            scheme_id=scheme_id,
            sections_count=len(cleaned_document.get('sections', []))
        )
        
        try:
            sections = cleaned_document.get('sections', [])
            chunks = []
            
            for section in sections:
                section_name = section.get('name', '')
                section_text = section.get('text', '')
                
                if not section_name or not section_text.strip():
                    logger.warning(
                        "Skipping empty section",
                        scheme_id=scheme_id,
                        section_name=section_name
                    )
                    continue
                
                # Apply section-specific chunking strategy
                section_chunks = self._chunk_section(section, scheme_id)
                chunks.extend(section_chunks)
            
            logger.info(
                "Document chunking completed",
                scheme_id=scheme_id,
                total_chunks=len(chunks)
            )
            
            return chunks
            
        except Exception as e:
            logger.error(
                "Document chunking failed",
                scheme_id=scheme_id,
                error=str(e)
            )
            raise
    
    def _chunk_section(self, section: Dict, scheme_id: str) -> List[Dict]:
        """
        Chunk a single section with semantic boundary detection.
        
        Args:
            section: Section data with name and text
            scheme_id: Scheme identifier
            
        Returns:
            List of chunks for this section
        """
        section_name = section.get('name', '')
        section_text = section.get('text', '')
        section_source = section.get('source', 'html_section')
        
        # Estimate token count
        estimated_tokens = len(section_text) // 4
        
        if estimated_tokens <= self.soft_cap_tokens:
            # Section fits in one chunk - no splitting needed
            chunk = self._create_chunk(
                section_name=section_name,
                section_text=section_text,
                section_source=section_source,
                scheme_id=scheme_id,
                chunk_index=0
            )
            return [chunk]
        
        elif estimated_tokens <= self.hard_cap_tokens:
            # Section fits in one chunk with some margin
            chunk = self._create_chunk(
                section_name=section_name,
                section_text=section_text,
                section_source=section_source,
                scheme_id=scheme_id,
                chunk_index=0
            )
            return [chunk]
        
        # Section needs to be split - use semantic chunking
        return self._semantic_chunk_section(section, scheme_id)
    
    def _semantic_chunk_section(self, section: Dict, scheme_id: str) -> List[Dict]:
        """
        Semantically chunk a section with overlap and boundary detection.
        """
        section_name = section.get('name', '')
        section_text = section.get('text', '')
        section_source = section.get('source', 'html_section')
        
        # Split into sentences first
        sentences = self._split_into_sentences(section_text)
        
        chunks = []
        current_chunk_text = ""
        current_chunk_tokens = 0
        chunk_index = 0
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = len(sentence) // 4
            
            # Check if adding this sentence would exceed hard cap
            if current_chunk_tokens + sentence_tokens + self.overlap_tokens > self.hard_cap_tokens:
                # Save current chunk and start new one
                if current_chunk_text.strip():
                    chunk = self._create_chunk(
                        section_name=section_name,
                        section_text=current_chunk_text.strip(),
                        section_source=section_source,
                        scheme_id=scheme_id,
                        chunk_index=chunk_index
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                current_chunk_text = sentence + " "
                current_chunk_tokens = sentence_tokens + self.overlap_tokens
                chunk_index += 1
            else:
                # Add to current chunk
                current_chunk_text += sentence + " "
                current_chunk_tokens += sentence_tokens
        
        # Handle remaining text
        if current_chunk_text.strip():
            chunk = self._create_chunk(
                section_name=section_name,
                section_text=current_chunk_text.strip(),
                section_source=section_source,
                scheme_id=scheme_id,
                chunk_index=chunk_index
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences while preserving numeric facts.
        """
        # First, split by common sentence endings
        sentences = re.split(r'[.!?]+', text)
        
        # Refine sentences to keep numeric facts together
        refined_sentences = []
        for sentence in sentences:
            # Don't split numeric facts like "₹14,615.19 Cr"
            if re.search(r'₹[\d,\.]+\s*Cr|[A-Z]\s*\d+\.?\d*\s*Cr', sentence):
                refined_sentences.append(sentence)
            else:
                # Further split long sentences
                if len(sentence) > 200:
                    # Split by commas or semicolons within long sentences
                    parts = re.split(r'[,;]', sentence)
                    for part in parts:
                        if part.strip():
                            refined_sentences.append(part.strip())
                else:
                    refined_sentences.append(sentence.strip())
        
        return [s.strip() for s in refined_sentences if s.strip()]
    
    def _create_chunk(
        self,
        section_name: str,
        section_text: str,
        section_source: str,
        scheme_id: str,
        chunk_index: int
    ) -> Dict:
        """Create a chunk with proper metadata."""
        
        return {
            "chunk_id": str(uuid.uuid4()),
            "scheme_id": scheme_id,
            "scheme_name": self._get_scheme_name(scheme_id),
            "doc_type": "Product_Page",
            "source_url": self._get_source_url(scheme_id),
            "section": section_name,
            "section_source": section_source,
            "last_updated": datetime.now().isoformat(),
            "content_hash": self._compute_content_hash(section_text),
            "stable_content_hash": self._get_stable_content_hash(scheme_id),
            "text": section_text.strip(),
            "token_count": len(section_text) // 4,
            "chunk_index": chunk_index
        }
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_scheme_name(self, scheme_id: str) -> str:
        """Get scheme name from configuration."""
        try:
            from src.utils.config import config_manager
            sources = config_manager.load_sources()
            for scheme in sources.get('schemes', []):
                if scheme.get('id') == scheme_id:
                    return scheme.get('name', scheme_id)
        except Exception:
            return scheme_id
    
    def _get_source_url(self, scheme_id: str) -> str:
        """Get source URL for a scheme ID."""
        try:
            from src.utils.config import config_manager
            sources = config_manager.load_sources()
            for scheme in sources.get('schemes', []):
                if scheme.get('id') == scheme_id:
                    for source in scheme.get('sources', []):
                        return source.get('url')
        except Exception:
            return ""
    
    def _get_stable_content_hash(self, scheme_id: str) -> str:
        """Get stable content hash from Phase 1.3 metadata."""
        try:
            metadata_file = Path(f"data/processed/{scheme_id}/structured_metadata.json")
            if metadata_file.exists():
                import json
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get('stable_content_hash', '')
        except Exception:
            return ""


class Chunker:
    """Main chunker class for processing documents."""
    
    def __init__(self, soft_cap: int = 250, hard_cap: int = 400, overlap: int = 30):
        self.content_chunker = ContentChunker(soft_cap, hard_cap, overlap)
    
    def chunk_documents(self, cleaned_documents: List[Dict]) -> List[Dict]:
        """
        Chunk multiple cleaned documents.
        
        Args:
            cleaned_documents: List of cleaned documents from Phase 1.3
            
        Returns:
            List of all chunks from all documents
        """
        logger.info(
            "Starting batch chunking",
            document_count=len(cleaned_documents)
        )
        
        all_chunks = []
        
        for doc in cleaned_documents:
            try:
                scheme_id = doc.get('scheme_id', '')
                chunks = self.content_chunker.chunk_document(doc, scheme_id)
                all_chunks.extend(chunks)
                
                logger.info(
                    "Chunked document",
                    scheme_id=scheme_id,
                    chunks_count=len(chunks)
                )
                
            except Exception as e:
                logger.error(
                    "Failed to chunk document",
                    scheme_id=doc.get('scheme_id', ''),
                    error=str(e)
                )
        
        logger.info(
            "Batch chunking completed",
            total_chunks=len(all_chunks)
        )
        
        return all_chunks
    
    def save_chunks(self, chunks: List[Dict]) -> None:
        """
        Save chunks to JSONL format with statistics.
        
        Args:
            chunks: List of chunk dictionaries
        """
        try:
            # Group chunks by scheme for statistics
            scheme_stats = {}
            for chunk in chunks:
                scheme_id = chunk.get('scheme_id', '')
                if scheme_id not in scheme_stats:
                    scheme_stats[scheme_id] = {
                        "count": 0,
                        "total_tokens": 0,
                        "sections": set()
                    }
                
                scheme_stats[scheme_id]["count"] += 1
                scheme_stats[scheme_id]["total_tokens"] += chunk.get("token_count", 0)
                scheme_stats[scheme_id]["sections"].add(chunk.get("section", ""))
            
            # Save chunks to JSONL file
            output_dir = Path("data/processed")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            chunks_file = output_dir / "chunks.jsonl"
            with open(chunks_file, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk) + '\n')
            
            # Save statistics
            stats = {
                "total_chunks": len(chunks),
                "schemes": {sid: {
                    "count": stats["count"],
                    "total_tokens": stats["total_tokens"],
                    "sections": list(stats["sections"])
                } for sid, stats in scheme_stats.items()},
                "chunking_stats": {
                    "soft_cap": self.content_chunker.soft_cap,
                    "hard_cap": self.content_chunker.hard_cap,
                    "overlap": self.content_chunker.overlap,
                    "average_chunk_size": sum(c.get("token_count", 0) for c in chunks) // len(chunks) if chunks else 0
                }
            }
            
            stats_file = output_dir / "chunking_stats.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            
            logger.info(
                "Chunks saved",
                total_chunks=len(chunks),
                chunks_file=str(chunks_file),
                stats_file=str(stats_file)
            )
            
        except Exception as e:
            logger.error(
                "Failed to save chunks",
                error=str(e)
            )
            raise
