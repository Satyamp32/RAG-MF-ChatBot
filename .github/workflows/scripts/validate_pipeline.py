#!/usr/bin/env python3
"""
Pipeline Validation Script for GitHub Actions

Validates pipeline outputs and provides detailed feedback.
"""

import pandas as pd
import sys
from pathlib import Path

def validate_embeddings():
    """Validate embeddings file."""
    embeddings_path = Path("data/index/embeddings.parquet")
    if not embeddings_path.exists():
        print("❌ Embeddings file not found")
        return False
    
    try:
        df = pd.read_parquet(embeddings_path)
        print(f"✅ Embeddings found: {len(df)}")
        
        # Check embedding dimensions
        if 'embedding' in df.columns:
            sample_embedding = df['embedding'].iloc[0]
            if len(sample_embedding) == 384:
                print("✅ Embedding dimension correct: 384")
                return True
            else:
                print(f"❌ Wrong embedding dimension: {len(sample_embedding)}")
                return False
        else:
            print("❌ Embeddings not found")
            return False
    except Exception as e:
        print(f"❌ Error validating embeddings: {e}")
        return False

def main():
    """Main validation function."""
    print("=== Pipeline Validation ===")
    
    # Check critical files
    critical_files = [
        "data/processed/chunks.json",
        "data/index/embeddings.parquet", 
        "data/index/chroma",
        "data/logs/refresh_log.json"
    ]
    
    validation_passed = True
    for file_path in critical_files:
        if not Path(file_path).exists():
            print(f"❌ Missing critical file: {file_path}")
            validation_passed = False
    
    # Validate chunk count
    chunks_path = Path("data/processed/chunks.json")
    if chunks_path.exists():
        with open(chunks_path, 'r') as f:
            chunk_count = sum(1 for line in f if line.strip())
        
        if chunk_count < 20:
            print(f"⚠️ Low chunk count: {chunk_count} (expected ~35)")
        else:
            print(f"✅ Good chunk count: {chunk_count}")
    
    # Validate embeddings
    embeddings_valid = validate_embeddings()
    if not embeddings_valid:
        validation_passed = False
    
    # Set exit status
    if validation_passed:
        print("✅ Pipeline validation passed")
        sys.exit(0)
    else:
        print("❌ Pipeline validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
