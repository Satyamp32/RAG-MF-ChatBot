"""
Integration Tests for Phase 2 and Phase 3

Tests the complete retrieval and reasoning pipeline
for mutual fund RAG system.
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from retrieval.hybrid_retriever import HybridRetriever
from retrieval.evaluator import RetrievalEvaluator
from reasoning.orchestrator import ReasoningOrchestrator
from reasoning.guardrails import Guardrails
from retrieval.query_processor import QueryProcessor


class TestPhase2Phase3Integration:
    """Integration tests for Phase 2 (Retrieval) and Phase 3 (Reasoning)"""
    
    @pytest.fixture
    def sample_chunks(self):
        """Sample chunks for testing."""
        return [
            {
                'chunk_id': 'hdfc_equity_1',
                'scheme_id': 'hdfc_equity',
                'section': 'Expense Ratio',
                'text': 'The expense ratio of HDFC Equity Fund is 1.11% per annum.',
                'score': 0.85,
                'confidence': 0.9,
                'metadata': {
                    'source_url': 'https://groww.in/mutual-funds/hdfc-equity-fund'
                }
            },
            {
                'chunk_id': 'hdfc_equity_2',
                'scheme_id': 'hdfc_equity',
                'section': 'Minimum Investment',
                'text': 'The minimum SIP amount is ₹500 per month and minimum lumpsum investment is ₹5000.',
                'score': 0.75,
                'confidence': 0.8,
                'metadata': {
                    'source_url': 'https://groww.in/mutual-funds/hdfc-equity-fund'
                }
            },
            {
                'chunk_id': 'hdfc_mid_cap_1',
                'scheme_id': 'hdfc_mid_cap',
                'section': 'Exit Load',
                'text': 'Exit load of 1% if redeemed within 365 days from the date of allotment.',
                'score': 0.65,
                'confidence': 0.7,
                'metadata': {
                    'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund'
                }
            }
        ]
    
    @pytest.fixture
    def test_queries(self):
        """Test queries for integration testing."""
        return [
            {
                'query': 'What is the expense ratio of HDFC Equity Fund?',
                'expected_scheme': 'hdfc_equity',
                'expected_section': 'Expense Ratio',
                'query_type': 'numerical_heavy'
            },
            {
                'query': 'What is the minimum SIP amount for HDFC Equity Fund?',
                'expected_scheme': 'hdfc_equity',
                'expected_section': 'Minimum Investment',
                'query_type': 'numerical_heavy'
            },
            {
                'query': 'Tell me about the exit load of HDFC Mid Cap Fund',
                'expected_scheme': 'hdfc_mid_cap',
                'expected_section': 'Exit Load',
                'query_type': 'section_specific'
            },
            {
                'query': 'Which HDFC fund has the lowest expense ratio?',
                'expected_scheme': 'multiple',
                'expected_section': 'Expense Ratio',
                'query_type': 'semantic'
            }
        ]
    
    def test_query_processor(self, test_queries):
        """Test query processing functionality."""
        processor = QueryProcessor()
        
        for test_query in test_queries:
            result = processor.normalize_query(test_query['query'])
            
            # Basic validation
            assert result['original'] == test_query['query']
            assert result['normalized'] is not None
            assert result['query_type'] in ['numerical_heavy', 'section_specific', 'semantic', 'general']
            
            # Check for expected query type
            if 'expense ratio' in test_query['query'].lower():
                assert 'expense_ratio' in result['sections']
            
            if 'hdfc equity' in test_query['query'].lower():
                scheme_ids = [s['scheme_id'] for s in result['schemes']]
                assert 'hdfc_equity' in scheme_ids
    
    def test_guardrails(self):
        """Test guardrails functionality."""
        guardrails = Guardrails()
        
        # Test PII detection
        pii_text = "My PAN is ABCD1234E and email is test@example.com"
        pii_result = guardrails.check_pii(pii_text)
        assert pii_result['has_pii'] is True
        assert 'pan_card' in pii_result['pii_types']
        assert 'email' in pii_result['pii_types']
        
        # Test hallucination detection
        hallucination_text = "I cannot find this information but I think the return is 15%"
        hallucination_result = guardrails.check_hallucination(hallucination_text, ['test context'])
        assert hallucination_result['hallucination_score'] > 0.0
        
        # Test banned tokens
        banned_text = "I would recommend investing in this fund for better returns"
        banned_result = guardrails.check_banned_tokens(banned_text)
        assert banned_result['has_banned'] is True
        assert 'recommend' in banned_result['banned_tokens']
    
    @pytest.mark.asyncio
    async def test_hybrid_retriever_initialization(self):
        """Test hybrid retriever initialization."""
        retriever = HybridRetriever(
            dense_weight=0.4,
            sparse_weight=0.6,
            top_k=5,
            enable_reranking=True
        )
        
        # Test initialization without vector store (mock)
        # This would normally initialize with actual vector store
        assert retriever.dense_weight == 0.4
        assert retriever.sparse_weight == 0.6
        assert retriever.top_k == 5
        assert retriever.enable_reranking is True
    
    @pytest.mark.asyncio
    async def test_reasoning_orchestrator_initialization(self):
        """Test reasoning orchestrator initialization."""
        orchestrator = ReasoningOrchestrator(use_groq='false')  # Test extractive mode
        
        assert orchestrator.use_groq == 'false'
        assert orchestrator.guardrails is not None
    
    @pytest.mark.asyncio
    async def test_extractive_response_generation(self, sample_chunks):
        """Test extractive response generation."""
        orchestrator = ReasoningOrchestrator(use_groq='false')
        
        query = "What is the expense ratio of HDFC Equity Fund?"
        
        response = await orchestrator.generate_response(query, sample_chunks)
        
        # Validate response structure
        assert response is not None
        assert 'success' in response
        assert 'metadata' in response
        
        if response['success']:
            assert 'response' in response
            assert 'content' in response['response']
            assert 'confidence' in response
            assert response['metadata']['generation_method'] == 'extractive'
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, test_queries, sample_chunks):
        """Test complete end-to-end pipeline."""
        # Initialize components
        processor = QueryProcessor()
        orchestrator = ReasoningOrchestrator(use_groq='false')
        
        # Test each query
        for test_query in test_queries:
            # Process query
            processed_query = processor.normalize_query(test_query['query'])
            
            # Generate response
            response = await orchestrator.generate_response(
                test_query['query'], 
                sample_chunks,
                processed_query['query_type']
            )
            
            # Validate response
            assert response is not None
            assert 'success' in response
            assert 'metadata' in response
            
            # Check metadata
            metadata = response['metadata']
            assert metadata['query'] == test_query['query']
            assert metadata['chunks_used'] == len(sample_chunks)
            assert metadata['generation_method'] in ['extractive', 'groq']
            assert 'timestamp' in metadata
    
    def test_retrieval_evaluation(self, sample_chunks):
        """Test retrieval evaluation functionality."""
        evaluator = RetrievalEvaluator()
        
        # Create test query results
        test_results = [
            {
                'query': 'What is the expense ratio of HDFC Equity Fund?',
                'expected_scheme': 'hdfc_equity',
                'expected_section': 'Expense Ratio'
            }
        ]
        
        # Test single query evaluation
        evaluation = evaluator._evaluate_single_query(
            'What is the expense ratio of HDFC Equity Fund?',
            sample_chunks,
            'hdfc_equity',
            'Expense Ratio'
        )
        
        assert 'retrieved_relevant' in evaluation
        assert 'precision_at_1' in evaluation
        assert 'precision_at_5' in evaluation
        assert 'mrr' in evaluation
        
        # Should find relevant chunk
        assert evaluation['precision_at_1'] > 0.0
    
    def test_confidence_scoring(self, sample_chunks):
        """Test confidence scoring functionality."""
        orchestrator = ReasoningOrchestrator(use_groq='false')
        
        # Test confidence extraction from response
        high_confidence_response = "Based on the context, the expense ratio is 1.11%"
        low_confidence_response = "I do not have enough information about this"
        
        high_score = orchestrator._extract_confidence_from_response(high_confidence_response)
        low_score = orchestrator._extract_confidence_from_response(low_confidence_response)
        
        assert high_score > low_score
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= low_score <= 1.0
    
    def test_source_attribution(self, sample_chunks):
        """Test source attribution functionality."""
        orchestrator = ReasoningOrchestrator(use_groq='false')
        
        response = "The expense ratio is 1.11%"
        
        attributed_response = orchestrator._add_source_attribution(response, sample_chunks)
        
        assert 'Source:' in attributed_response
        assert 'Last updated from sources:' in attributed_response
    
    @pytest.mark.asyncio
    async def test_guardrails_integration(self, sample_chunks):
        """Test guardrails integration with response generation."""
        guardrails = Guardrails()
        
        # Create a response with PII
        response_with_pii = {
            'content': 'My PAN is ABCD1234E and the expense ratio is 1.11%',
            'confidence': 0.8,
            'source': 'test',
            'last_updated': '2024-01-01'
        }
        
        context = ['test context']
        
        # Should fail due to PII
        validated = guardrails.sanitize_response(response_with_pii, context)
        assert validated['success'] is False
        assert 'PII detected' in validated['reason']
        
        # Create a valid response
        valid_response = {
            'content': 'The expense ratio is 1.11%',
            'confidence': 0.8,
            'source': 'https://groww.in/mutual-funds/hdfc-equity-fund',
            'last_updated': '2024-01-01'
        }
        
        # Should pass
        validated = guardrails.sanitize_response(valid_response, context)
        assert validated['success'] is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
