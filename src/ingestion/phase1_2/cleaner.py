"""
Phase 1.2 - HTML Cleaning & Normalization

Implements HTML content cleaning, boilerplate removal, and content normalization
for mutual fund data processing.
"""

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from bs4 import BeautifulSoup

from src.utils.config import config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ContentCleaner:
    """HTML content cleaner with boilerplate removal and normalization."""
    
    def __init__(self):
        # Known boilerplate patterns to remove
        self.boilerplate_patterns = [
            "Mutual fund investments are subject to market risks",
            "You may also like",
            "Read more",
            "Related articles",
            "Disclaimer",
            "Invest Now",
            "Apply Now",
            "Start SIP",
            "Explore more funds",
            "View all funds",
            "Download application",
            "Contact us",
            "Follow us on",
            "Subscribe to newsletter",
            "Terms and conditions",
            "Privacy policy",
            "Cookie policy"
        ]
        
        # Volatile field patterns (fields that change frequently)
        self.volatile_patterns = [
            r'NAV.*?\s*[:=]\s*[\d,\.]+\s*',
            r'as on.*?\s*[:=]\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'AUM.*?\s*[:=]\s*[\d,\.]+\s*Cr?',
            r'Net Assets.*?\s*[:=]\s*[\d,\.]+\s*Cr?',
            r'Fund Size.*?\s*[:=]\s*[\d,\.]+\s*Cr?',
            r'Launch Date.*?\s*[:=]\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'Category.*?\s*[:=]\s*\w+',
            r'Risk Level.*?\s*[:=]\s*\w+',
            r'Scheme Type.*?\s*[:=]\s*\w+'
        ]
        
        # Currency normalization patterns
        self.currency_patterns = [
            (r'Rs\.?\s*([\d,\.]+)', r'₹\1'),
            (r'INR\s*([\d,\.]+)', r'₹\1'),
            (r'₹\s*([\d,\.]+)', r'₹\1'),
            (r'Rs\.?\s*([\d,\.]+)\s*Cr?', r'₹\1 Cr'),
            (r'INR\s*([\d,\.]+)\s*Cr?', r'₹\1 Cr')
        ]
        
        # Number and percentage normalization
        self.number_patterns = [
            (r'(\d+\.?\d*)%\s*', r'\1%'),
            (r'(\d+\.?\d*)\s*%', r'\1%'),
            (r'(\d+\.?\d*)\s*percent', r'\1%')
        ]
        
        # Special character normalization
        self.special_char_patterns = [
            (r'[–—]', '-'),  # En dash and em dash
            (r'[""]', '"'),  # Smart quotes
            (r'['']', "'"),    # Smart single quotes
            (r'\s+', ' ')     # Multiple spaces
        ]
    
    def clean_html(self, html_content: str, scheme_id: str) -> Dict:
        """
        Clean HTML content by removing boilerplate and normalizing text.
        
        Args:
            html_content: Raw HTML content from Phase 1.1
            scheme_id: Scheme identifier for logging
            
        Returns:
            Dictionary with cleaned content and metadata
        """
        logger.info(
            "Starting HTML cleaning",
            scheme_id=scheme_id,
            content_length=len(html_content)
        )
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Remove common boilerplate elements
            for element in soup.find_all(['nav', 'footer', 'header', 'aside', 'advertisement']):
                element.decompose()
            
            # Get main content
            main_content = soup.get_text(separator=' ', strip=True)
            
            # Apply cleaning transformations
            cleaned_content = self._apply_cleaning_transformations(main_content)
            
            # Extract and clean sections
            sections = self._extract_sections(soup)
            
            # Determine extraction health
            extraction_health = self._assess_extraction_health(sections)
            
            result = {
                "scheme_id": scheme_id,
                "source_url": self._get_source_url(scheme_id),
                "fetched_at": datetime.now().isoformat(),
                "sections": sections,
                "extraction_health": extraction_health,
                "cleaning_stats": {
                    "original_length": len(html_content),
                    "cleaned_length": len(cleaned_content),
                    "boilerplate_removed": len(html_content) - len(cleaned_content),
                    "sections_found": len(sections)
                }
            }
            
            logger.info(
                "HTML cleaning completed",
                scheme_id=scheme_id,
                sections_count=len(sections),
                health=extraction_health
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "HTML cleaning failed",
                scheme_id=scheme_id,
                error=str(e)
            )
            raise
    
    def _apply_cleaning_transformations(self, content: str) -> str:
        """Apply various text cleaning transformations."""
        
        # Unicode normalization
        content = unicodedata.normalize('NFKC', content)
        
        # Remove boilerplate phrases
        for pattern in self.boilerplate_patterns:
            content = re.sub(re.escape(pattern), '', content, flags=re.IGNORECASE)
        
        # Normalize currency
        for pattern, replacement in self.currency_patterns:
            content = re.sub(pattern[0], pattern[1], content)
        
        # Normalize percentages
        for pattern in self.number_patterns:
            content = re.sub(pattern[0], pattern[1], content)
        
        # Normalize special characters
        for pattern, replacement in self.special_char_patterns:
            content = re.sub(pattern[0], replacement, content)
        
        # Collapse multiple spaces
        content = re.sub(r'\s+', ' ', content)
        
        # Strip leading/trailing whitespace
        content = content.strip()
        
        return content
    
    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract relevant sections from cleaned HTML."""
        
        # Define section selectors based on common Groww patterns
        section_selectors = {
            "Scheme Details": ["h1", "h2", ".scheme-details"],
            "Expense Ratio": [".expense-ratio", ".expense", "th:contains('Expense')"],
            "Exit Load": [".exit-load", ".exit", "th:contains('Exit')"],
            "Minimum Investment": [".min-investment", ".minimum", "th:contains('Minimum')"],
            "Riskometer": [".riskometer", ".risk", "th:contains('Risk')"],
            "Fund Manager": [".fund-manager", ".manager", "th:contains('Manager')"],
            "Fund House": [".fund-house", ".amc", "th:contains('House')"],
            "About": [".about", ".description", "th:contains('About')"],
            "Benchmark": [".benchmark", ".performance", "th:contains('Benchmark')"],
            "Tax": [".tax", "th:contains('Tax')"]
        }
        
        sections = []
        
        for section_name, selectors in section_selectors.items():
            section_content = self._extract_section_content(soup, section_name, selectors)
            if section_content and section_content.strip():
                sections.append({
                    "name": section_name,
                    "text": section_content.strip(),
                    "source": "html_section"
                })
        
        return sections
    
    def _extract_section_content(self, soup: BeautifulSoup, section_name: str, selectors: List[str]) -> str:
        """Extract content for a specific section."""
        
        for selector in selectors:
            # Try different selector strategies
            elements = soup.select(selector)
            if elements:
                # Get text from all matching elements
                content_parts = []
                for element in elements:
                    text = element.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                
                if content_parts:
                    return ' '.join(content_parts)
            
            # Try heading-based extraction
            heading = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and 
                           section_name.lower() in tag.get_text(strip=True).lower())
            if heading:
                # Get content after heading until next heading
                content_parts = []
                next_sibling = heading.next_sibling
                while next_sibling and next_sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    if hasattr(next_sibling, 'get_text'):
                        text = next_sibling.get_text(strip=True)
                        if text:
                            content_parts.append(text)
                    next_sibling = next_sibling.next_sibling
                
                if content_parts:
                    return ' '.join(content_parts)
        
        return ""
    
    def _assess_extraction_health(self, sections: List[Dict]) -> str:
        """Assess the health of section extraction."""
        
        if not sections:
            return "failed"
        
        # Must-have sections for mutual fund data
        must_have_sections = ["Scheme Details", "Expense Ratio", "Exit Load", "Minimum Investment"]
        
        found_sections = [s["name"] for s in sections]
        missing_sections = [s for s in must_have_sections if s not in found_sections]
        
        if missing_sections:
            logger.warning(
                "Missing must-have sections",
                missing_sections=missing_sections,
                found_sections=found_sections
            )
            return "degraded"
        
        # Check for empty sections
        empty_sections = [s["name"] for s in sections if not s["text"].strip()]
        if empty_sections:
            logger.warning(
                "Empty sections found",
                empty_sections=empty_sections
            )
            return "degraded"
        
        return "ok"
    
    def _get_source_url(self, scheme_id: str) -> str:
        """Get source URL for a scheme ID."""
        try:
            sources = config_manager.load_sources()
            for scheme in sources.get('schemes', []):
                if scheme.get('id') == scheme_id:
                    for source in scheme.get('sources', []):
                        return source.get('url')
        except Exception as e:
            logger.warning(
                "Failed to get source URL",
                scheme_id=scheme_id,
                error=str(e)
            )
        return ""
    
    def remove_volatile_fields(self, content: str) -> str:
        """Remove volatile fields that change frequently."""
        
        for pattern in self.volatile_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        return content
    
    def calculate_stable_hash(self, content: str) -> str:
        """Calculate hash of content with volatile fields removed."""
        stable_content = self.remove_volatile_fields(content)
        import hashlib
        return hashlib.sha256(stable_content.encode('utf-8')).hexdigest()


class Cleaner:
    """Main cleaner class for processing HTML content."""
    
    def __init__(self):
        self.content_cleaner = ContentCleaner()
    
    def clean_document(self, extracted_data: Dict, scheme_id: str) -> Dict:
        """
        Clean extracted document data and apply section-specific rules.
        
        Args:
            extracted_data: Raw extracted data from Phase 1.2
            scheme_id: Scheme identifier
            
        Returns:
            Cleaned document data with section-specific processing
        """
        logger.info(
            "Starting document cleaning",
            scheme_id=scheme_id,
            sections_count=len(extracted_data.get('sections', []))
        )
        
        try:
            cleaned_sections = []
            
            for section in extracted_data.get('sections', []):
                section_name = section.get('name', '')
                section_text = section.get('text', '')
                
                # Apply section-specific cleaning rules
                cleaned_section = self._apply_section_rules(section_name, section_text)
                
                if cleaned_section.strip():
                    cleaned_sections.append({
                        "name": section_name,
                        "text": cleaned_section,
                        "source": section.get('source', 'html_section')
                    })
            
            # Calculate stable content hash
            all_text = ' '.join([s['text'] for s in cleaned_sections])
            stable_hash = self.content_cleaner.calculate_stable_hash(all_text)
            
            result = {
                "scheme_id": scheme_id,
                "source_url": extracted_data.get('source_url', ''),
                "fetched_at": extracted_data.get('fetched_at', ''),
                "sections": cleaned_sections,
                "stable_content_hash": stable_hash,
                "cleaning_health": self._assess_cleaning_health(cleaned_sections),
                "processing_stats": {
                    "original_sections": len(extracted_data.get('sections', [])),
                    "cleaned_sections": len(cleaned_sections),
                    "volatile_fields_removed": len(self.content_cleaner.volatile_patterns)
                }
            }
            
            logger.info(
                "Document cleaning completed",
                scheme_id=scheme_id,
                cleaned_sections=len(cleaned_sections),
                stable_hash=stable_hash[:8] + "..."
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Document cleaning failed",
                scheme_id=scheme_id,
                error=str(e)
            )
            raise
    
    def _apply_section_rules(self, section_name: str, section_text: str) -> str:
        """Apply section-specific cleaning rules."""
        
        if not section_text:
            return section_text
        
        cleaned_text = section_text
        
        # Apply general cleaning transformations
        cleaned_text = self.content_cleaner._apply_cleaning_transformations(cleaned_text)
        
        # Section-specific rules
        if section_name == "Fund Manager":
            # Keep only name and tenure, remove bio details
            cleaned_text = self._clean_fund_manager_section(cleaned_text)
        elif section_name == "Fund House":
            # Keep only AMC name, rank, AUM, incorporation date
            cleaned_text = self._clean_fund_house_section(cleaned_text)
        elif section_name == "FAQ":
            # Drop FAQ section entirely (not part of facts-only corpus)
            cleaned_text = ""
        
        return cleaned_text
    
    def _clean_fund_manager_section(self, text: str) -> str:
        """Clean fund manager section to keep only essential info."""
        
        # Keep only name and tenure patterns
        patterns_to_keep = [
            r'([A-Z]+\s+[A-Z]+\s+[A-Z]+\s*-\s*Present)',  # Name with tenure
            r'([A-Z]+\s+[A-Z]+\s+[A-Z]+\s+\d{4}\s*-\s*Present)',  # Name with join year
            r'Experience:\s*\d+\s*years?',  # Experience years
            r'Tenure:\s*\d+\s*years?'  # Tenure
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns_to_keep):
                # Further clean to keep only essential info
                line = re.sub(r'\s+', ' ', line)  # Normalize spaces
                line = re.sub(r'(Experience|Tenure):', '', line)  # Remove labels
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines)
    
    def _clean_fund_house_section(self, text: str) -> str:
        """Clean fund house section to keep only essential info."""
        
        # Keep only AMC name, rank, AUM, incorporation date
        patterns_to_keep = [
            r'([A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+Fund)',  # AMC name
            r'Rank:\s*\d+',  # Rank
            r'AUM:\s*[\d,\.]+\s*Cr?',  # AUM
            r'Incorporated:\s*\d{4}',  # Incorporation date
            r'Established:\s*\d{4}',  # Establishment date
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns_to_keep):
                # Further clean to standardize format
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines)
    
    def _assess_cleaning_health(self, sections: List[Dict]) -> str:
        """Assess the health of cleaning process."""
        
        if not sections:
            return "failed"
        
        # Check for FAQ section (should be removed)
        faq_sections = [s for s in sections if s.get('name') == 'FAQ']
        if faq_sections:
            logger.warning(
                "FAQ sections found (should be removed)",
                faq_count=len(faq_sections)
            )
            return "degraded"
        
        # Check for empty sections
        empty_sections = [s for s in sections if not s.get('text', '').strip()]
        if empty_sections:
            logger.warning(
                "Empty sections after cleaning",
                empty_sections=[s.get('name') for s in empty_sections]
            )
            return "degraded"
        
        return "ok"
