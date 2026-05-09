"""
Phase 1.5 - Embedding Generation

Implements dense vector generation for chunks with model versioning,
batch processing, and quality validation for mutual fund RAG.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from src.utils.config import config_manager
from src.utils.logger import get_logger
from src.utils.retry import TemporaryError, retry

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for chunks using BAAI/bge-small-en model."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en", batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = None
        self.embedding_dim = 384  # bge-small-en dimension
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model with error handling."""
        try:
            logger.info(
                "Loading embedding model",
                model_name=self.model_name
            )
            self.model = SentenceTransformer(self.model_name)
            
            # Test model with sample text
            test_embedding = self.model.encode("test", convert_to_numpy=True)
            
            if test_embedding.shape[0] != self.embedding_dim:
                raise ValueError(f"Expected dimension {self.embedding_dim}, got {test_embedding.shape[0]}")
            
            logger.info(
                "Model loaded successfully",
                model_name=self.model_name,
                embedding_dim=test_embedding.shape[0]
            )
            
        except Exception as e:
            logger.error(
                "Failed to load embedding model",
                model_name=self.model_name,
                error=str(e)
            )
            raise
    
    @retry(max_attempts=3, delay=1.0, backoff=2.0, exception_types=(TemporaryError,))
    def generate_embeddings_batch(self, chunks: List[Dict]) -> List[Dict]:
        """
        Generate embeddings for a batch of chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of chunks with embeddings added
        """
        logger.info(
            "Starting batch embedding generation",
            chunk_count=len(chunks),
            batch_size=self.batch_size
        )
        
        try:
            # Prepare texts for embedding
            texts = []
            for chunk in chunks:
                # Prepend scheme name to avoid near-duplicate clustering
                scheme_name = chunk.get('scheme_name', '')
                chunk_text = chunk.get('text', '')
                
                if scheme_name:
                    text = f"{scheme_name}\n\n{chunk_text}"
                else:
                    text = chunk_text
                
                texts.append(text)
            
            # Generate embeddings in batches
            all_embeddings = []
            
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i + self.batch_size]
                
                logger.debug(
                    "Processing embedding batch",
                    batch_start=i,
                    batch_end=min(i + self.batch_size, len(texts)),
                    batch_size=len(batch_texts)
                )
                
                # Generate embeddings
                embeddings = self.model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # Normalize for cosine similarity
                    show_progress_bar=False
                )
                
                all_embeddings.extend(embeddings)
            
            # Add embeddings to chunks
            embedded_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
                embedded_chunk = chunk.copy()
                embedded_chunk['embedding'] = embedding.tolist()
                embedded_chunk['embedding_model'] = self.model_name
                embedded_chunk['embedding_dim'] = self.embedding_dim
                embedded_chunk['embedding_normalized'] = True
                embedded_chunk['embedding_generated_at'] = datetime.now().isoformat()
                
                embedded_chunks.append(embedded_chunk)
            
            logger.info(
                "Batch embedding generation completed",
                total_chunks=len(chunks),
                embedding_dim=self.embedding_dim,
                model_name=self.model_name
            )
            
            return embedded_chunks
            
        except Exception as e:
            logger.error(
                "Batch embedding generation failed",
                chunk_count=len(chunks),
                error=str(e)
            )
            raise TemporaryError(f"Embedding generation failed: {str(e)}")
    
    def validate_embeddings(self, embedded_chunks: List[Dict]) -> Dict:
        """
        Validate generated embeddings for quality and consistency.
        
        Args:
            embedded_chunks: List of chunks with embeddings
            
        Returns:
            Validation results with statistics
        """
        logger.info(
            "Starting embedding validation",
            chunk_count=len(embedded_chunks)
        )
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        try:
            # Check embedding dimensions
            for i, chunk in enumerate(embedded_chunks):
                embedding = chunk.get('embedding', [])
                
                if not embedding:
                    validation_result["errors"].append(f"Chunk {i}: Missing embedding")
                    validation_result["is_valid"] = False
                    continue
                
                if len(embedding) != self.embedding_dim:
                    validation_result["errors"].append(
                        f"Chunk {i}: Expected dimension {self.embedding_dim}, got {len(embedding)}"
                    )
                    validation_result["is_valid"] = False
                
                # Check for NaN or infinite values
                if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
                    validation_result["errors"].append(f"Chunk {i}: Invalid embedding values")
                    validation_result["is_valid"] = False
            
            # Calculate statistics
            if embedded_chunks:
                embeddings = np.array([chunk['embedding'] for chunk in embedded_chunks])
                
                validation_result["statistics"] = {
                    "total_embeddings": len(embedded_chunks),
                    "embedding_dimension": self.embedding_dim,
                    "mean_norm": np.mean(np.linalg.norm(embeddings, axis=1)),
                    "std_norm": np.std(np.linalg.norm(embeddings, axis=1)),
                    "min_value": float(np.min(embeddings)),
                    "max_value": float(np.max(embeddings)),
                    "mean_value": float(np.mean(embeddings)),
                    "std_value": float(np.std(embeddings))
                }
            
            logger.info(
                "Embedding validation completed",
                is_valid=validation_result["is_valid"],
                errors_count=len(validation_result["errors"]),
                warnings_count=len(validation_result["warnings"])
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(
                "Embedding validation failed",
                error=str(e)
            )
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
            return validation_result


class Embedder:
    """Main embedder class for processing chunks."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en", batch_size: int = 32):
        self.embedding_generator = EmbeddingGenerator(model_name, batch_size)
    
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Generate embeddings for all chunks with validation.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of chunks with embeddings
        """
        logger.info(
            "Starting chunk embedding",
            total_chunks=len(chunks)
        )
        
        try:
            # Generate embeddings in batches
            embedded_chunks = []
            
            for i in range(0, len(chunks), self.embedding_generator.batch_size):
                batch_chunks = chunks[i:i + self.embedding_generator.batch_size]
                
                logger.info(
                    "Processing chunk batch",
                    batch_start=i,
                    batch_end=min(i + self.embedding_generator.batch_size, len(chunks))
                )
                
                batch_embedded = self.embedding_generator.generate_embeddings_batch(batch_chunks)
                embedded_chunks.extend(batch_embedded)
            
            # Validate all embeddings
            validation_result = self.embedding_generator.validate_embeddings(embedded_chunks)
            
            if not validation_result["is_valid"]:
                logger.error(
                    "Embedding validation failed",
                    errors=validation_result["errors"]
                )
                raise ValueError("Generated embeddings failed validation")
            
            logger.info(
                "Chunk embedding completed",
                total_chunks=len(embedded_chunks),
                validation_passed=validation_result["is_valid"]
            )
            
            return embedded_chunks
            
        except Exception as e:
            logger.error(
                "Chunk embedding failed",
                error=str(e)
            )
            raise
    
    def save_embeddings(self, embedded_chunks: List[Dict]) -> None:
        """
        Save embeddings to parquet format with metadata.
        
        Args:
            embedded_chunks: List of chunks with embeddings
        """
        try:
            import pandas as pd
            
            # Prepare data for saving
            embedding_data = []
            metadata = {
                "model_name": self.embedding_generator.model_name,
                "embedding_dim": self.embedding_generator.embedding_dim,
                "total_chunks": len(embedded_chunks),
                "generated_at": datetime.now().isoformat(),
                "batch_size": self.embedding_generator.batch_size
            }
            
            for chunk in embedded_chunks:
                # Create row for parquet
                row = {
                    "chunk_id": chunk["chunk_id"],
                    "scheme_id": chunk["scheme_id"],
                    "scheme_name": chunk.get("scheme_name", ""),
                    "section": chunk["section"],
                    "text": chunk["text"],
                    "token_count": chunk.get("token_count", 0),
                    "embedding": chunk["embedding"],
                    "content_hash": chunk["content_hash"],
                    "stable_content_hash": chunk["stable_content_hash"],
                    "embedding_model": chunk["embedding_model"],
                    "embedding_dim": chunk["embedding_dim"],
                    "embedding_generated_at": chunk["embedding_generated_at"]
                }
                embedding_data.append(row)
            
            # Create output directory
            output_dir = Path("data/index")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save embeddings as parquet
            df = pd.DataFrame(embedding_data)
            embeddings_file = output_dir / "embeddings.parquet"
            df.to_parquet(embeddings_file, index=False)
            
            # Save metadata
            metadata_file = output_dir / "embedder.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            # Save chunks as JSONL for reference
            chunks_file = output_dir / "chunks_with_embeddings.jsonl"
            with open(chunks_file, 'w', encoding='utf-8') as f:
                for chunk in embedded_chunks:
                    # Remove embedding from JSONL to save space
                    chunk_copy = chunk.copy()
                    chunk_copy.pop('embedding', None)
                    f.write(json.dumps(chunk_copy) + '\n')
            
            logger.info(
                "Embeddings saved successfully",
                embeddings_file=str(embeddings_file),
                metadata_file=str(metadata_file),
                chunks_file=str(chunks_file),
                total_chunks=len(embedded_chunks)
            )
            
        except Exception as e:
            logger.error(
                "Failed to save embeddings",
                error=str(e)
            )
            raise
    
    def load_embeddings(self) -> Tuple[List[Dict], Dict]:
        """
        Load embeddings from saved files.
        
        Returns:
            Tuple of (embedded_chunks, metadata)
        """
        try:
            import pandas as pd
            
            output_dir = Path("data/index")
            embeddings_file = output_dir / "embeddings.parquet"
            metadata_file = output_dir / "embedder.json"
            
            # Load embeddings
            if embeddings_file.exists():
                df = pd.read_parquet(embeddings_file)
                embedded_chunks = df.to_dict('records')
            else:
                embedded_chunks = []
            
            # Load metadata
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            logger.info(
                "Embeddings loaded successfully",
                total_chunks=len(embedded_chunks),
                metadata_file=str(metadata_file)
            )
            
            return embedded_chunks, metadata
            
        except Exception as e:
            logger.error(
                "Failed to load embeddings",
                error=str(e)
            )
            return [], {}
