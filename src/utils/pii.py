"""
PII (Personally Identifiable Information) detection and redaction utilities.
"""

import re
from typing import List, Tuple, Dict, Any

import structlog

logger = structlog.get_logger(__name__)


class PIIDetector:
    """Detects and redacts personally identifiable information."""
    
    def __init__(self):
        # Compile regex patterns for PII detection
        self.patterns = {
            'pan': re.compile(
                r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',
                re.IGNORECASE
            ),
            'aadhaar': re.compile(
                r'\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b',
                re.IGNORECASE
            ),
            'email': re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                re.IGNORECASE
            ),
            'phone': re.compile(
                r'(\+91[-\s]?)?[0-9]{10}|(\+91[-\s]?)?[0-9]{3}[-\s]?[0-9]{3}[-\s]?[0-9]{4}',
                re.IGNORECASE
            ),
            'account_number': re.compile(
                r'\b[A-Z]{4}[0-9]{6,8}\b',
                re.IGNORECASE
            ),
            'otp': re.compile(
                r'\b[0-9]{4,8}\b(?=\s*(is|are|your|code|pin|password))',
                re.IGNORECASE
            )
        }
        
        # Redaction token
        self.redaction_token = "[REDACTED]"
    
    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """
        Detect PII in text.
        
        Args:
            text: Input text to scan
            
        Returns:
            Dictionary with PII types as keys and list of matches as values
        """
        detected = {}
        
        for pii_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                detected[pii_type] = matches
                logger.warning(
                    "PII detected in text",
                    pii_type=pii_type,
                    match_count=len(matches)
                )
        
        return detected
    
    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.
        
        Args:
            text: Input text to check
            
        Returns:
            True if PII is detected, False otherwise
        """
        detected = self.detect_pii(text)
        return bool(detected)
    
    def redact_pii(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Redact PII from text.
        
        Args:
            text: Input text to redact
            
        Returns:
            Tuple of (redacted_text, redaction_counts)
        """
        redacted_text = text
        redaction_counts = {}
        
        for pii_type, pattern in self.patterns.items():
            matches = pattern.findall(redacted_text)
            if matches:
                redacted_text = pattern.sub(self.redaction_token, redacted_text)
                redaction_counts[pii_type] = len(matches)
                logger.info(
                    "Redacted PII from text",
                    pii_type=pii_type,
                    count=len(matches)
                )
        
        return redacted_text, redaction_counts
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate a user query for PII.
        
        Args:
            query: User query to validate
            
        Returns:
            Validation result with PII information
        """
        detected = self.detect_pii(query)
        
        return {
            'is_valid': not bool(detected),
            'has_pii': bool(detected),
            'pii_types': list(detected.keys()),
            'pii_matches': detected,
            'redacted_query': self.redact_pii(query)[0] if detected else query
        }


# Global PII detector instance
pii_detector = PIIDetector()


def sanitize_input(text: str) -> str:
    """
    Sanitize input text by removing PII.
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized text with PII redacted
    """
    return pii_detector.redact_pii(text)[0]


def is_safe_input(text: str) -> bool:
    """
    Check if input text is safe (no PII).
    
    Args:
        text: Input text to check
        
    Returns:
        True if safe, False if PII detected
    """
    return not pii_detector.has_pii(text)
