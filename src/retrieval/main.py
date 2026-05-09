"""
Main entry point for Phase 2 - Retrieval Layer.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.hybrid_retriever import HybridRetriever
from retrieval.evaluator import RetrievalEvaluator
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Main function for Phase 2 retrieval layer."""
    
    parser = argparse.ArgumentParser(description="Phase 2 - Retrieval Layer")
    parser.add_argument(
        "query",
        type=str,
        help="Query to retrieve mutual fund information"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top results to retrieve"
    )
    parser.add_argument(
        "--scheme-filter",
        type=str,
        help="Filter by specific scheme ID"
    )
    parser.add_argument(
        "--section-filter",
        type=str,
        help="Filter by specific section"
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run retrieval evaluation"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize retriever
        retriever = HybridRetriever(
            dense_weight=0.4,
            sparse_weight=0.6,
            top_k=args.top_k,
            enable_reranking=True
        )
        
        # Initialize vector store
        initialized = await retriever.initialize()
        if not initialized:
            print("❌ Failed to initialize retriever")
            return
        
        if args.evaluate:
            # Run evaluation mode
            await run_evaluation(retriever)
        else:
            # Run single query
            if not args.query:
                print("❌ Error: Query is required for retrieval mode")
                return
            
            await run_retrieval(retriever, args)
            
    except Exception as e:
        logger.error(
            "Retrieval execution failed",
            error=str(e)
        )
        print(f"❌ Fatal Error: {str(e)}")
        sys.exit(1)


async def run_retrieval(retriever: HybridRetriever, args):
    """Run retrieval for a single query."""
    
    query = args.query
    top_k = args.top_k
    scheme_filter = getattr(args, 'scheme_filter', None)
    section_filter = getattr(args, 'section_filter', None)
    
    logger.info(
        "Starting retrieval",
        query=query,
        top_k=top_k,
        scheme_filter=scheme_filter,
        section_filter=section_filter
    )
    
    # Prepare filters
    where_filter = {}
    if scheme_filter:
        where_filter['scheme_id'] = scheme_filter
    if section_filter:
        where_filter['section'] = section_filter
    
    # Perform retrieval
    results = await retriever.retrieve(
        query=query,
        scheme_filter=scheme_filter,
        section_filter=section_filter,
        top_k=top_k
    )
    
    # Display results
    print(f"\n=== Retrieval Results for: '{query}' ===")
    print(f"Query Type: {results[0].get('query_type', 'unknown') if results else 'unknown'}")
    print(f"Top-K: {len(results)}")
    
    if results:
        print(f"\nTop {len(results)} Results:")
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            confidence = result.get('confidence', 0)
            scheme_id = result.get('scheme_id', 'N/A')
            section = result.get('section', 'N/A')
            source = result.get('source', 'unknown')
            
            print(f"\n{i}. Score: {score:.3f} | Confidence: {confidence:.2f}")
            print(f"   Scheme: {scheme_id}")
            print(f"   Section: {section}")
            print(f"   Source: {source}")
            print(f"   Text: {result.get('text', '')[:200]}...")
    else:
        print("No results found")
    
    print(f"\n=== Retrieval Complete ===")


async def run_evaluation(retriever: HybridRetriever):
    """Run comprehensive retrieval evaluation."""
    
    logger.info("Starting retrieval evaluation")
    
    # Initialize evaluator
    evaluator = RetrievalEvaluator()
    
    # Create test queries
    test_queries = evaluator.create_test_queries()
    
    # Run evaluation
    results = await evaluator.evaluate_retrieval(
        retriever=retriever,
        test_queries=test_queries
    )
    
    # Print results
    evaluator.print_evaluation_summary(results)
    
    # Save detailed results
    evaluator.save_evaluation_results(
        results,
        "data/evaluation/retrieval_results.json"
    )
    
    print(f"\n=== Retrieval Evaluation Complete ===")
    print(f"Results saved to: data/evaluation/retrieval_results.json")


if __name__ == "__main__":
    asyncio.run(main())
