"""
Query Processor for Retrieval Layer

Handles query normalization, scheme resolution, and numerical token extraction
for mutual fund RAG system.
"""

import re
from typing import Dict, List, Optional, Tuple

from src.utils.config import config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class QueryProcessor:
    """Processes user queries for optimal retrieval."""
    
    def __init__(self):
        # Mutual fund specific patterns
        self.mf_tokens = [
            'ELSS', 'SIP', 'NAV', 'AUM', 'CR', 'LAK', 'FUND', 'MF', 'AMC'
        ]
        
        # Numerical patterns for extraction
        self.numerical_patterns = [
            r'(\d+(?:\.\d+)?)\s*%',  # percentages
            r'₹\s*([\d,\.]+)',  # currency amounts
            r'(\d+(?:\.\d+)?)\s*years?',  # time periods
            r'(\d+(?:\.\d+)?)\s*months?',  # time periods
        ]
        
        # Section-specific keywords
        self.section_keywords = {
            'expense_ratio': ['expense ratio', 'expense', 'ratio', 'fees', 'charges'],
            'exit_load': ['exit load', 'exit', 'load', 'withdrawal'],
            'minimum_investment': ['minimum', 'sip', 'lumpsum', 'investment', 'invest'],
            'risk_level': ['risk', 'riskometer', 'conservative', 'moderate', 'aggressive'],
            'fund_manager': ['manager', 'fund manager', 'who manages', 'amc'],
            'returns': ['returns', 'performance', 'growth', 'profit', 'gain'],
            'fund_details': ['details', 'information', 'about', 'objective', 'category'],
            'tax': ['tax', 'taxation', 'capital gains', 'dividend'],
            'benchmark': ['benchmark', 'index', 'comparison', 'nifty', 'sensex']
        }
    
    def normalize_query(self, query: str) -> Dict:
        """
        Normalize query for optimal retrieval.
        
        Args:
            query: Raw user query
            
        Returns:
            Dictionary with normalized components
        """
        logger.info(
            "Normalizing query",
            original_query=query[:100] + "..." if len(query) > 100 else query
        )
        
        normalized = {
            'original': query,
            'normalized': query,
            'lowercase': query.lower(),
            'tokens': [],
            'schemes': [],
            'sections': [],
            'numerical_data': {},
            'query_type': 'general'
        }
        
        # Basic normalization
        normalized_query = self._basic_normalization(query)
        normalized['normalized'] = normalized_query
        
        # Extract tokens
        normalized['tokens'] = self._extract_mf_tokens(normalized_query)
        
        # Resolve schemes
        normalized['schemes'] = self._resolve_schemes(normalized_query)
        
        # Identify sections
        normalized['sections'] = self._identify_sections(normalized_query)
        
        # Extract numerical data
        normalized['numerical_data'] = self._extract_numerical_data(normalized_query)
        
        # Determine query type
        normalized['query_type'] = self._classify_query_type(
            normalized['tokens'], 
            normalized['sections'], 
            normalized['numerical_data']
        )
        
        logger.info(
            "Query normalization completed",
            query_type=normalized['query_type'],
            tokens_count=len(normalized['tokens']),
            schemes_count=len(normalized['schemes']),
            sections_count=len(normalized['sections'])
        )
        
        return normalized
    
    def _basic_normalization(self, query: str) -> str:
        """Apply basic text normalization."""
        # Unicode normalization
        import unicodedata
        normalized = unicodedata.normalize('NFKC', query)
        
        # Case folding
        normalized = normalized.lower()
        
        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        
        # Normalize currency symbols
        normalized = re.sub(r'rs\.?\s*', '₹', normalized)
        normalized = re.sub(r'rs\.?\s*', '₹', normalized)
        
        return normalized
    
    def _extract_mf_tokens(self, query: str) -> List[str]:
        """Extract mutual fund specific tokens."""
        tokens = []
        query_lower = query.lower()
        
        for token in self.mf_tokens:
            if token.lower() in query_lower:
                tokens.append(token)
        
        return list(set(tokens))  # Remove duplicates
    
    def _resolve_schemes(self, query: str) -> List[Dict]:
        """
        Resolve mutual fund schemes mentioned in query.
        
        Uses longest substring matching against scheme names and aliases.
        """
        try:
            sources = config_manager.load_sources()
            schemes = sources.get('schemes', [])
            
            resolved_schemes = []
            query_lower = query.lower()
            
            for scheme in schemes:
                scheme_id = scheme.get('id', '')
                scheme_name = scheme.get('name', '')
                aliases = scheme.get('aliases', [])
                
                # Check exact matches first
                if scheme_id.lower() in query_lower:
                    resolved_schemes.append({
                        'scheme_id': scheme_id,
                        'scheme_name': scheme_name,
                        'match_type': 'exact_id',
                        'match_text': scheme_id,
                        'confidence': 1.0
                    })
                    continue
                
                if scheme_name.lower() in query_lower:
                    resolved_schemes.append({
                        'scheme_id': scheme_id,
                        'scheme_name': scheme_name,
                        'match_type': 'exact_name',
                        'match_text': scheme_name,
                        'confidence': 1.0
                    })
                    continue
                
                # Check aliases
                for alias in aliases:
                    if alias.lower() in query_lower:
                        resolved_schemes.append({
                            'scheme_id': scheme_id,
                            'scheme_name': scheme_name,
                            'match_type': 'alias',
                            'match_text': alias,
                            'confidence': 0.9
                        })
                        break
                
                # Longest substring matching
                for word in query_lower.split():
                    if len(word) >= 3:  # Only match meaningful substrings
                        if word in scheme_name.lower():
                            match_length = len(word)
                            scheme_length = len(scheme_name)
                            confidence = match_length / scheme_length
                            
                            if confidence > 0.5:  # Minimum confidence threshold
                                resolved_schemes.append({
                                    'scheme_id': scheme_id,
                                    'scheme_name': scheme_name,
                                    'match_type': 'substring',
                                    'match_text': word,
                                    'confidence': confidence
                                })
            
            # Remove duplicates and sort by confidence
            unique_schemes = []
            seen_schemes = set()
            
            for scheme in resolved_schemes:
                if scheme['scheme_id'] not in seen_schemes:
                    unique_schemes.append(scheme)
                    seen_schemes.add(scheme['scheme_id'])
            
            # Sort by confidence (descending)
            unique_schemes.sort(key=lambda x: x['confidence'], reverse=True)
            
            logger.info(
                "Scheme resolution completed",
                total_matches=len(unique_schemes),
                unique_schemes=len(seen_schemes)
            )
            
            return unique_schemes
            
        except Exception as e:
            logger.error(
                "Scheme resolution failed",
                error=str(e)
            )
            return []
    
    def _identify_sections(self, query: str) -> List[str]:
        """Identify mutual fund sections mentioned in query."""
        identified_sections = []
        query_lower = query.lower()
        
        for section_name, keywords in self.section_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    identified_sections.append(section_name)
                    break  # Only add each section once
        
        return list(set(identified_sections))
    
    def _extract_numerical_data(self, query: str) -> Dict:
        """Extract numerical data from query."""
        numerical_data = {}
        
        for pattern_name, pattern in [
            ('percentages', r'(\d+(?:\.\d+)?)\s*%'),
            ('currency', r'₹\s*([\d,\.]+)'),
            ('years', r'(\d+(?:\.\d+)?)\s*years?'),
            ('months', r'(\d+(?:\.\d+)?)\s*months?')
        ]:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                numerical_data[pattern_name] = [float(m) for m in matches]
        
        return numerical_data
    
    def _classify_query_type(self, tokens: List[str], sections: List[str], numerical_data: Dict) -> str:
        """
        Classify query type for optimal retrieval strategy.
        
        Returns: 'numerical', 'semantic', 'mixed', 'general'
        """
        has_numerical = bool(numerical_data)
        has_sections = bool(sections)
        has_tokens = bool(tokens)
        
        # Priority classification
        if has_numerical and len(numerical_data) > 1:
            return 'numerical_heavy'
        elif has_numerical:
            return 'numerical'
        elif has_sections:
            return 'section_specific'
        elif has_tokens:
            return 'token_specific'
        else:
            return 'general'
    
    def get_section_boosts(self, query: str, sections: List[str]) -> Dict[str, float]:
        """Get section-based score boosts for retrieval."""
        boosts = {}
        query_lower = query.lower()
        
        for section in sections:
            if section in self.section_keywords:
                keywords = self.section_keywords[section]
                for keyword in keywords:
                    if keyword in query_lower:
                        boosts[section] = 0.2  # Boost score by 20%
                        break
        
        return boosts
    
    def get_scheme_confidence_scores(self, schemes: List[Dict]) -> Dict[str, float]:
        """Get confidence scores for resolved schemes."""
        scores = {}
        
        for scheme in schemes:
            scheme_id = scheme['scheme_id']
            confidence = scheme.get('confidence', 0.0)
            scores[scheme_id] = confidence
        
        return scores
