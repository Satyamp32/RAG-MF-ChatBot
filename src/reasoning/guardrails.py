"""
Guardrails for Reasoning Layer

Implements hallucination prevention, PII protection, and
response validation for mutual fund RAG system.
"""

import re
from typing import Dict, List, Optional

from src.utils.config import config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Guardrails:
    """Implements safety and compliance checks for responses."""
    
    def __init__(self):
        # PII patterns for detection
        self.pii_patterns = [
            # PAN card pattern (simplified)
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            # Aadhaar pattern (12 digits)
            r'\b\d{12}\b',
            # Email pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # Phone pattern (Indian mobile)
            r'\b[6-9]\d{9}\b',
            # OTP pattern
            r'\b(?:OTP|One Time Password|verification code)\b.*\d{4,6}',
            # Bank account pattern
            r'\b(?:account|acc|a/c)\s*no?\s*\d{8,16}\b',
            # Credit card pattern
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        ]
        
        # Hallucination indicators
        self.hallucination_indicators = [
            'i cannot find',
            'i do not have access',
            'i am not sure',
            'it is recommended',
            'you should consider',
            'please consult',
            'this is not financial advice',
            'i am an ai',
            'as an ai language model'
        ]
        
        # Banned tokens for financial advice
        self.banned_tokens = [
            'recommend', 'should', 'must', 'need to', 'better than',
            'will outperform', 'guaranteed', 'promise', 'assured',
            'best investment', 'worst investment', 'top pick', 'hot tip'
        ]
        
        # Required response elements
        self.required_elements = ['content', 'source', 'last_updated']
    
    def check_pii(self, text: str) -> Dict:
        """Check for PII in text."""
        pii_detected = []
        
        for pattern_name, pattern in [
            ('pan_card', self.pii_patterns[0]),
            ('aadhaar', self.pii_patterns[1]),
            ('email', self.pii_patterns[2]),
            ('phone', self.pii_patterns[3]),
            ('otp', self.pii_patterns[4]),
            ('bank_account', self.pii_patterns[5]),
            ('credit_card', self.pii_patterns[6])
        ]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                pii_detected.append({
                    'type': pattern_name,
                    'matches': matches,
                    'count': len(matches)
                })
        
        return {
            'has_pii': len(pii_detected) > 0,
            'pii_types': [p['type'] for p in pii_detected],
            'pii_details': pii_detected
        }
    
    def check_hallucination(self, text: str, context: List[str]) -> Dict:
        """Check for hallucination indicators."""
        hallucination_score = 0.0
        detected_indicators = []
        
        text_lower = text.lower()
        
        # Check for hallucination phrases
        for indicator in self.hallucination_indicators:
            if indicator in text_lower:
                hallucination_score += 0.3
                detected_indicators.append(indicator)
        
        # Check for information not in context
        context_text = ' '.join(context).lower()
        for word in text_lower.split():
            if len(word) > 3 and word not in context_text:
                hallucination_score += 0.1
        
        # Check for numerical values not in context
        numbers_in_response = re.findall(r'\d+(?:\.\d+)?', text)
        numbers_in_context = re.findall(r'\d+(?:\.\d+)?', context_text)
        
        if len(numbers_in_response) > len(numbers_in_context):
            hallucination_score += 0.2
        
        return {
            'hallucination_score': min(hallucination_score, 1.0),
            'detected_indicators': detected_indicators,
            'is_hallucinated': hallucination_score > 0.5
        }
    
    def check_banned_tokens(self, text: str) -> Dict:
        """Check for banned tokens in text."""
        text_lower = text.lower()
        found_banned = []
        
        for token in self.banned_tokens:
            if token in text_lower:
                found_banned.append(token)
        
        return {
            'has_banned': len(found_banned) > 0,
            'banned_tokens': found_banned
        }
    
    def validate_response_structure(self, response: Dict) -> Dict:
        """Validate response structure and required elements."""
        validation_result = {
            'is_valid': True,
            'missing_elements': [],
            'extra_elements': [],
            'structure_issues': []
        }
        
        # Check required elements
        for element in self.required_elements:
            if element not in response:
                validation_result['is_valid'] = False
                validation_result['missing_elements'].append(element)
        
        # Check content length
        content = response.get('content', '')
        if len(content) > 500:
            validation_result['structure_issues'].append('Response too long (>500 chars)')
        
        # Check sentence count
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) > 3:
            validation_result['structure_issues'].append('Too many sentences (>3)')
        
        # Check for URLs
        urls = re.findall(r'https?://[^\s]+', content)
        if len(urls) > 1:
            validation_result['structure_issues'].append('Multiple URLs detected')
        elif len(urls) == 1:
            # Check if URL is whitelisted
            url = urls[0]
            if not self._is_whitelisted_url(url):
                validation_result['structure_issues'].append('Non-whitelisted URL detected')
        
        return validation_result
    
    def _is_whitelisted_url(self, url: str) -> bool:
        """Check if URL is in the whitelist."""
        try:
            sources = config_manager.load_sources()
            whitelisted_domains = []
            
            for scheme in sources.get('schemes', []):
                for source in scheme.get('sources', []):
                    source_url = source.get('url', '')
                    if source_url:
                        domain = re.findall(r'https?://([^/]+)', source_url)
                        if domain:
                            whitelisted_domains.append(domain[0])
            
            url_domain = re.findall(r'https?://([^/]+)', url)
            return url_domain[0] in whitelisted_domains if url_domain else False
            
        except Exception as e:
            logger.error(
                "Whitelist check failed",
                url=url,
                error=str(e)
            )
            return False
    
    def apply_confidence_gate(self, response: Dict, confidence_threshold: float = 0.3) -> Dict:
        """Apply confidence gate to response."""
        confidence = response.get('confidence', 0.0)
        
        if confidence < confidence_threshold:
            return {
                'should_respond': False,
                'reason': 'Low confidence',
                'threshold': confidence_threshold,
                'actual_confidence': confidence,
                'response': None
            }
        
        return {
            'should_respond': True,
            'reason': 'Confidence acceptable',
            'threshold': confidence_threshold,
            'actual_confidence': confidence,
            'response': response
        }
    
    def sanitize_response(self, response: Dict, context: List[str]) -> Dict:
        """Sanitize response based on guardrails."""
        content = response.get('content', '')
        
        # Check PII
        pii_check = self.check_pii(content)
        if pii_check['has_pii']:
            logger.warning(
                "PII detected in response",
                pii_types=pii_check['pii_types']
            )
            return {
                'success': False,
                'reason': 'PII detected',
                'pii_details': pii_check,
                'response': None
            }
        
        # Check hallucination
        hallucination_check = self.check_hallucination(content, context)
        if hallucination_check['is_hallucinated']:
            logger.warning(
                "Hallucination detected in response",
                score=hallucination_check['hallucination_score'],
                indicators=hallucination_check['detected_indicators']
            )
            return {
                'success': False,
                'reason': 'Hallucination detected',
                'hallucination_details': hallucination_check,
                'response': None
            }
        
        # Check banned tokens
        banned_check = self.check_banned_tokens(content)
        if banned_check['has_banned']:
            logger.warning(
                "Banned tokens detected in response",
                tokens=banned_check['banned_tokens']
            )
            return {
                'success': False,
                'reason': 'Banned tokens detected',
                'banned_details': banned_check,
                'response': None
            }
        
        # Validate structure
        structure_check = self.validate_response_structure(response)
        if not structure_check['is_valid']:
            logger.warning(
                "Response structure validation failed",
                issues=structure_check['structure_issues'],
                missing=structure_check['missing_elements']
            )
            return {
                'success': False,
                'reason': 'Structure validation failed',
                'structure_details': structure_check,
                'response': None
            }
        
        # Apply confidence gate
        confidence_gate = self.apply_confidence_gate(response)
        if not confidence_gate['should_respond']:
            logger.info(
                "Response blocked by confidence gate",
                confidence=confidence_gate['actual_confidence'],
                threshold=confidence_gate['threshold']
            )
            return {
                'success': False,
                'reason': 'Low confidence',
                'confidence_details': confidence_gate,
                'response': None
            }
        
        # All checks passed
        logger.info(
            "Response passed all guardrails",
            confidence=response.get('confidence', 0.0),
            content_length=len(content)
        )
        
        return {
            'success': True,
            'reason': 'All checks passed',
            'response': response
        }
