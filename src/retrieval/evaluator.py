"""
Retrieval Evaluation Utilities

Provides comprehensive evaluation metrics and testing utilities
for retrieval system quality assessment.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional
from pathlib import Path

import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RetrievalEvaluator:
    """Evaluates retrieval quality with multiple metrics."""
    
    def __init__(self):
        self.evaluation_metrics = [
            'precision_at_k',
            'recall_at_k',
            'mrr',
            'retrieval_time',
            'confidence_correlation',
            'section_accuracy',
            'scheme_accuracy'
        ]
    
    async def evaluate_retrieval(
        self,
        retriever,
        test_queries: List[Dict],
        ground_truth: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Evaluate retriever performance against test queries.
        
        Args:
            retriever: HybridRetriever instance
            test_queries: List of test queries with expected results
            ground_truth: Optional ground truth data for evaluation
            
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info(
            "Starting retrieval evaluation",
            query_count=len(test_queries),
            has_ground_truth=ground_truth is not None
        )
        
        evaluation_results = {
            'total_queries': len(test_queries),
            'successful_retrievals': 0,
            'failed_retrievals': 0,
            'precision_at_1': 0.0,
            'precision_at_5': 0.0,
            'recall_at_5': 0.0,
            'mrr': 0.0,
            'average_retrieval_time': 0.0,
            'section_accuracy': 0.0,
            'scheme_accuracy': 0.0,
            'confidence_correlation': 0.0,
            'query_results': []
        }
        
        total_retrieval_time = 0.0
        
        for i, test_query in enumerate(test_queries):
            try:
                query_text = test_query.get('query', '')
                expected_scheme = test_query.get('expected_scheme', '')
                expected_section = test_query.get('expected_section', '')
                
                # Perform retrieval
                start_time = time.time()
                results = await retriever.retrieve(
                    query=query_text,
                    top_k=5
                )
                retrieval_time = time.time() - start_time
                
                total_retrieval_time += retrieval_time
                
                # Evaluate retrieval quality
                query_evaluation = await self._evaluate_single_query(
                    query_text, results, expected_scheme, expected_section, ground_truth
                )
                
                # Update overall metrics
                if query_evaluation['retrieved_relevant']:
                    evaluation_results['successful_retrievals'] += 1
                else:
                    evaluation_results['failed_retrievals'] += 1
                
                evaluation_results['precision_at_1'] += query_evaluation['precision_at_1']
                evaluation_results['precision_at_5'] += query_evaluation['precision_at_5']
                evaluation_results['recall_at_5'] += query_evaluation['recall_at_5']
                evaluation_results['mrr'] += query_evaluation['mrr']
                evaluation_results['section_accuracy'] += query_evaluation['section_accuracy']
                evaluation_results['scheme_accuracy'] += query_evaluation['scheme_accuracy']
                evaluation_results['confidence_correlation'] += query_evaluation['confidence_correlation']
                
                evaluation_results['query_results'].append({
                    'query': query_text,
                    'expected_scheme': expected_scheme,
                    'expected_section': expected_section,
                    'retrieval_time': retrieval_time,
                    'results_count': len(results),
                    'evaluation': query_evaluation
                })
                
                logger.debug(
                    "Query evaluation completed",
                    query_index=i,
                    query=query_text[:50] + "..." if len(query_text) > 50 else query_text,
                    retrieved_count=len(results),
                    retrieval_time_ms=retrieval_time * 1000
                )
                
            except Exception as e:
                logger.error(
                    "Query evaluation failed",
                    query_index=i,
                    query=test_query.get('query', 'unknown'),
                    error=str(e)
                )
                evaluation_results['failed_retrievals'] += 1
                evaluation_results['query_results'].append({
                    'query': test_query.get('query', ''),
                    'error': str(e)
                })
        
        # Calculate final metrics
        if evaluation_results['total_queries'] > 0:
            evaluation_results['precision_at_1'] /= evaluation_results['total_queries']
            evaluation_results['precision_at_5'] /= evaluation_results['total_queries']
            evaluation_results['recall_at_5'] /= evaluation_results['total_queries']
            evaluation_results['mrr'] /= evaluation_results['total_queries']
            evaluation_results['section_accuracy'] /= evaluation_results['total_queries']
            evaluation_results['scheme_accuracy'] /= evaluation_results['total_queries']
            evaluation_results['confidence_correlation'] /= evaluation_results['total_queries']
            evaluation_results['average_retrieval_time'] = total_retrieval_time / evaluation_results['total_queries']
        
        logger.info(
            "Retrieval evaluation completed",
            total_queries=evaluation_results['total_queries'],
            success_rate=evaluation_results['successful_retrievals'] / evaluation_results['total_queries'],
            precision_at_1=evaluation_results['precision_at_1'],
            precision_at_5=evaluation_results['precision_at_5'],
            recall_at_5=evaluation_results['recall_at_5'],
            mrr=evaluation_results['mrr'],
            avg_time_ms=evaluation_results['average_retrieval_time'] * 1000
        )
        
        return evaluation_results
    
    async def _evaluate_single_query(
        self,
        query: str,
        results: List[Dict],
        expected_scheme: str,
        expected_section: str,
        ground_truth: Optional[List[Dict]]
    ) -> Dict:
        """Evaluate a single query retrieval."""
        
        evaluation = {
            'retrieved_relevant': False,
            'precision_at_1': 0.0,
            'precision_at_5': 0.0,
            'recall_at_5': 0.0,
            'mrr': 0.0,
            'section_accuracy': 0.0,
            'scheme_accuracy': 0.0,
            'confidence_correlation': 0.0
        }
        
        if not results:
            return evaluation
        
        # Check if top result is relevant
        top_result = results[0]
        if top_result:
            # Check scheme accuracy
            if expected_scheme and top_result.get('scheme_id') == expected_scheme:
                evaluation['scheme_accuracy'] = 1.0
            
            # Check section accuracy
            if expected_section and top_result.get('section') == expected_section:
                evaluation['section_accuracy'] = 1.0
            
            # Determine relevance
            evaluation['retrieved_relevant'] = (
                evaluation['scheme_accuracy'] > 0.5 or 
                evaluation['section_accuracy'] > 0.5
            )
        
        # Calculate precision@k
        retrieved_schemes = [r.get('scheme_id') for r in results]
        retrieved_sections = [r.get('section') for r in results]
        
        # Precision@1
        if expected_scheme in retrieved_schemes:
            evaluation['precision_at_1'] = 1.0
        
        # Precision@5
        relevant_retrieved = 0
        for i, result in enumerate(results[:5]):
            if (expected_scheme and result.get('scheme_id') == expected_scheme) or \
               (expected_section and result.get('section') == expected_section):
                relevant_retrieved += 1
                break  # Stop at first relevant result
        
        if relevant_retrieved > 0:
            evaluation['precision_at_5'] = 1.0 / (relevant_retrieved)
        else:
            evaluation['precision_at_5'] = 0.0
        
        # Calculate recall@5
        if ground_truth:
            relevant_total = len([gt for gt in ground_truth 
                                if gt.get('query', '').lower() in query.lower()])
            if relevant_total > 0:
                evaluation['recall_at_5'] = relevant_retrieved / relevant_total
        
        # Calculate MRR
        for i, result in enumerate(results[:5]):
            if (expected_scheme and result.get('scheme_id') == expected_scheme) or \
               (expected_section and result.get('section') == expected_section):
                evaluation['mrr'] = 1.0 / (i + 1)
                break
        
        # Calculate confidence correlation
        if results:
            scores = [r.get('confidence', 0) for r in results[:5]]
            if scores and evaluation['retrieved_relevant']:
                evaluation['confidence_correlation'] = np.corrcoef(
                    [1, 0.5, 0],  # Ideal scores for relevant results
                    scores[:3]  # Top 3 scores
                )[0, 1] if len(scores) >= 3 else (0, 0)
        
        return evaluation
    
    def create_test_queries(self) -> List[Dict]:
        """Create comprehensive test queries for mutual fund evaluation."""
        
        test_queries = [
            # Numerical queries
            {
                'query': 'What is the expense ratio of HDFC Equity Fund?',
                'expected_scheme': 'hdfc_equity',
                'expected_section': 'Expense Ratio',
                'query_type': 'numerical'
            },
            {
                'query': 'What is the minimum SIP amount for HDFC Mid Cap Fund?',
                'expected_scheme': 'hdfc_mid_cap',
                'expected_section': 'Minimum Investment',
                'query_type': 'numerical'
            },
            {
                'query': 'What is the exit load for HDFC Focused Fund?',
                'expected_scheme': 'hdfc_focused',
                'expected_section': 'Exit Load',
                'query_type': 'numerical'
            },
            
            # Section-specific queries
            {
                'query': 'Tell me about the fund manager of HDFC Equity Fund',
                'expected_scheme': 'hdfc_equity',
                'expected_section': 'Fund Manager',
                'query_type': 'section_specific'
            },
            {
                'query': 'What are the tax implications of HDFC ELSS Fund?',
                'expected_scheme': 'hdfc_elss',
                'expected_section': 'Tax',
                'query_type': 'section_specific'
            },
            {
                'query': 'What is the risk level of HDFC Large Cap Fund?',
                'expected_scheme': 'hdfc_large_cap',
                'expected_section': 'Risk Level',
                'query_type': 'section_specific'
            },
            
            # General/semantic queries
            {
                'query': 'Which HDFC fund has the lowest expense ratio?',
                'expected_scheme': 'multiple',  # Any HDFC fund
                'expected_section': 'Expense Ratio',
                'query_type': 'semantic'
            },
            {
                'query': 'Compare HDFC Equity and HDFC Focused Fund performance',
                'expected_scheme': 'multiple',  # Both funds
                'expected_section': 'multiple',  # Performance/Returns
                'query_type': 'semantic'
            },
            {
                'query': 'What is the investment objective of HDFC Mid Cap Fund?',
                'expected_scheme': 'hdfc_mid_cap',
                'expected_section': 'Fund Details',
                'query_type': 'semantic'
            }
        ]
        
        return test_queries
    
    def save_evaluation_results(self, results: Dict, output_path: str) -> None:
        """Save evaluation results to file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(
                "Evaluation results saved",
                output_path=str(output_file)
            )
            
        except Exception as e:
            logger.error(
                "Failed to save evaluation results",
                output_path=output_path,
                error=str(e)
            )
    
    def print_evaluation_summary(self, results: Dict) -> None:
        """Print evaluation summary in a readable format."""
        print(f"\n=== Retrieval Evaluation Summary ===")
        print(f"Total Queries: {results['total_queries']}")
        print(f"Successful Retrievals: {results['successful_retrievals']}")
        print(f"Failed Retrievals: {results['failed_retrievals']}")
        print(f"Success Rate: {results['successful_retrievals'] / results['total_queries']:.2%}")
        
        print(f"\n=== Precision Metrics ===")
        print(f"Precision@1: {results['precision_at_1']:.3f}")
        print(f"Precision@5: {results['precision_at_5']:.3f}")
        print(f"Recall@5: {results['recall_at_5']:.3f}")
        print(f"MRR: {results['mrr']:.3f}")
        
        print(f"\n=== Accuracy Metrics ===")
        print(f"Scheme Accuracy: {results['scheme_accuracy']:.3f}")
        print(f"Section Accuracy: {results['section_accuracy']:.3f}")
        print(f"Confidence Correlation: {results['confidence_correlation']:.3f}")
        
        print(f"\n=== Performance Metrics ===")
        print(f"Average Retrieval Time: {results['average_retrieval_time'] * 1000:.2f}ms")
        
        # Performance assessment
        if results['precision_at_1'] >= 0.8 and results['average_retrieval_time'] < 100:
            print("✅ Excellent retrieval performance")
        elif results['precision_at_1'] >= 0.6 and results['average_retrieval_time'] < 200:
            print("✅ Good retrieval performance")
        elif results['precision_at_1'] >= 0.4:
            print("⚠️  Acceptable retrieval performance")
        else:
            print("❌ Poor retrieval performance - needs improvement")
