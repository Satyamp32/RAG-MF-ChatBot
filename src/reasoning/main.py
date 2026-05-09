"""
Main entry point for Phase 3 - Reasoning & Guardrails.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from reasoning.orchestrator import ReasoningOrchestrator
from retrieval.hybrid_retriever import HybridRetriever
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 3 reasoning and guardrails."""
    
    parser = argparse.ArgumentParser(description="Phase 3 - Reasoning & Guardrails")
    parser.add_argument(
        "query",
        type=str,
        help="Query to process and generate response"
    )
    parser.add_argument(
        "--use-groq",
        type=str,
        default="auto",
        help="Use Groq LLM (auto, true, false)"
    )
    parser.add_argument(
        "--groq-model",
        type=str,
        default="llama3-70b-8192",
        help="Groq model to use"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--test-guardrails",
        action="store_true",
        help="Test guardrails with sample queries"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize orchestrator
        orchestrator = ReasoningOrchestrator(use_groq=args.use_groq)
        
        # Check if LLM is available
        if not orchestrator.llm_client and args.use_groq not in ["false", "extractive"]:
            print("❌ Error: Groq LLM not available. Check GROQ_API_KEY environment variable.")
            print("Set USE_GROQ=false to use extractive-only mode.")
            return
        
        if args.test_guardrails:
            # Run guardrails test
            await run_guardrails_test(orchestrator)
        else:
            # Run normal query processing
            if not args.query:
                print("❌ Error: Query is required")
                print("Use --test-guardrails to test guardrails functionality.")
                return
            
            # Initialize retriever
            retriever = HybridRetriever(top_k=args.top_k)
            await retriever.initialize()
            
            # Process query
            await run_query_processing(orchestrator, retriever, args.query)
            
    except Exception as e:
        logger.error(
            "Phase 3 execution failed",
            error=str(e)
        )
        print(f"❌ Fatal Error: {str(e)}")
        sys.exit(1)


async def run_guardrails_test(orchestrator: ReasoningOrchestrator):
    """Test guardrails with sample queries."""
    
    print("=== Testing Guardrails ===")
    
    test_queries = [
        # PII test
        "My PAN is ABCD1234E, what is my account balance?",
        # Hallucination test
        "What is the guaranteed return of 50% for all mutual funds?",
        # Banned tokens test
        "Which fund should I invest in for the best returns?",
        # Low confidence test
        "Tell me about XYZ fund that doesn't exist"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        
        # Create fake chunks for testing
        fake_chunks = [
            {
                "chunk_id": "test_1",
                "scheme_id": "hdfc_equity",
                "section": "Test Section",
                "text": "This is test content for guardrails testing.",
                "score": 0.8,
                "confidence": 0.7
            }
        ]
        
        # Generate response
        response = await orchestrator.generate_response(query, fake_chunks)
        
        # Check guardrails results
        if response.get('success'):
            print(f"✅ Response generated successfully")
            print(f"   Method: {response.get('metadata', {}).get('generation_method', 'unknown')}")
            print(f"   Confidence: {response.get('metadata', {}).get('confidence', 0.0):.2f}")
        else:
            print(f"❌ Response blocked by guardrails")
            print(f"   Reason: {response.get('reason', 'Unknown')}")
        
        # Show response content (truncated)
        content = response.get('response', '')
        if content:
            print(f"   Content: {content[:200]}{'...' if len(content) > 200 else ''}")


async def run_query_processing(orchestrator: ReasoningOrchestrator, retriever: HybridRetriever, query: str):
    """Run complete query processing pipeline."""
    
    print(f"\n=== Processing Query: '{query}' ===")
    
    # Retrieve relevant chunks
    print("Retrieving relevant chunks...")
    retrieved_chunks = await retriever.retrieve(query)
    
    if not retrieved_chunks:
        print("❌ No relevant chunks found")
        return
    
    print(f"✅ Retrieved {len(retrieved_chunks)} chunks")
    
    # Show top 3 chunks summary
    print("\nTop Retrieved Chunks:")
    for i, chunk in enumerate(retrieved_chunks[:3], 1):
        score = chunk.get('score', 0.0)
        scheme_id = chunk.get('scheme_id', 'N/A')
        section = chunk.get('section', 'N/A')
        confidence = chunk.get('confidence', 0.0)
        
        print(f"{i}. Score: {score:.3f} | Confidence: {confidence:.2f}")
        print(f"   Scheme: {scheme_id}")
        print(f"   Section: {section}")
        print(f"   Text: {chunk.get('text', '')[:150]}...")
    
    # Generate response
    print("\nGenerating response...")
    response = await orchestrator.generate_response(query, retrieved_chunks)
    
    if response.get('success'):
        print("\n=== Generated Response ===")
        print(f"Method: {response.get('metadata', {}).get('generation_method', 'unknown')}")
        print(f"Confidence: {response.get('metadata', {}).get('confidence', 0.0):.2f}")
        print(f"Timestamp: {response.get('metadata', {}).get('timestamp', 'N/A')}")
        
        content = response.get('response', '')
        if content:
            print(f"\nResponse:\n{content}")
        
        # Show source attribution
        if 'source_chunk' in response:
            source_chunk = response['source_chunk']
            print(f"\nSource Attribution:")
            print(f"Scheme: {source_chunk.get('scheme_id', 'N/A')}")
            print(f"Section: {source_chunk.get('section', 'N/A')}")
    else:
        print(f"\n❌ Response Generation Failed")
        print(f"Reason: {response.get('reason', 'Unknown')}")
        if 'error' in response:
            print(f"Error: {response['error']}")


if __name__ == "__main__":
    asyncio.run(main())
