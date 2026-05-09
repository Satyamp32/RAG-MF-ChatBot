"""
Phase 1.3 - Structured Mutual Fund Metadata Extraction

Implements extraction of structured mutual fund information including
NAV, fund category, risk level, expense ratio, fund manager,
returns, fund description, and holdings.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from decimal import Decimal

import structlog
from bs4 import BeautifulSoup

from src.utils.config import config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MutualFundExtractor:
    """Extracts structured mutual fund metadata from cleaned HTML."""
    
    def __init__(self):
        # Define field extraction patterns
        self.nav_patterns = [
            r'NAV[:\s]*([₹\d,\.]+|\d+\.?\d*)',
            r'Net Asset Value[:\s]*([₹\d,\.]+|\d+\.?\d*)',
            r'Current NAV[:\s]*([₹\d,\.]+|\d+\.?\d*)'
        ]
        
        self.percentage_patterns = [
            r'(\d+\.?\d*)%\s*',
            r'(\d+\.?\d*)\s*percent',
            r'Expense Ratio[:\s]*([₹\d,\.]+|\d+\.?\d*)\s*%?'
        ]
        
        self.currency_patterns = [
            r'([₹\d,\.]+|\d+\.?\d*)\s*Cr?',
            r'([₹\d,\.]+|\d+\.?\d*)\s*crore?',
            r'Rs\.?\s*([₹\d,\.]+|\d+\.?\d*)',
            r'INR\s*([₹\d,\.]+|\d+\.?\d*)'
        ]
        
        self.date_patterns = [
            r'(\d{2}[-/]\d{2}[-/]\d{4})',  # YYYY-MM-DD
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # D-M-YYYY
            r'(\d{4}[-/]\d{1,2}[-/]\d{2})'   # YYYY-MM-DD
        ]
        
        self.risk_patterns = [
            r'Risk[:\s]*([A-Z]+)',
            r'Risk Level[:\s]*([A-Z]+)',
            r'Riskometer[:\s]*([A-Z]+)'
        ]
        
        self.category_patterns = [
            r'Category[:\s]*([A-Z\s&\s]+)',
            r'Fund Type[:\s]*([A-Z\s&\s]+)',
            r'Scheme Type[:\s]*([A-Z\s&\s]+)'
        ]
    
    def extract_fund_metadata(self, cleaned_document: Dict, scheme_id: str) -> Dict:
        """
        Extract structured mutual fund metadata from cleaned document.
        
        Args:
            cleaned_document: Cleaned document from Phase 1.2
            scheme_id: Scheme identifier
            
        Returns:
            Structured metadata with all fund information
        """
        logger.info(
            "Starting metadata extraction",
            scheme_id=scheme_id,
            sections_count=len(cleaned_document.get('sections', []))
        )
        
        try:
            sections = {s['name']: s['text'] for s in cleaned_document.get('sections', [])}
            
            # Extract basic information
            metadata = {
                "scheme_id": scheme_id,
                "source_url": cleaned_document.get('source_url', ''),
                "fetched_at": cleaned_document.get('fetched_at', ''),
                "extraction_health": "ok",
                "basic_info": self._extract_basic_info(sections),
                "nav_details": self._extract_nav_details(sections),
                "financial_metrics": self._extract_financial_metrics(sections),
                "risk_info": self._extract_risk_info(sections),
                "category_info": self._extract_category_info(sections),
                "manager_info": self._extract_manager_info(sections),
                "fund_house_info": self._extract_fund_house_info(sections),
                "description": self._extract_description(sections),
                "holdings": self._extract_holdings(sections),
                "benchmark_info": self._extract_benchmark_info(sections),
                "returns_info": self._extract_returns_info(sections),
                "tax_info": self._extract_tax_info(sections),
                "min_investment_info": self._extract_min_investment_info(sections),
                "exit_load_info": self._extract_exit_load_info(sections),
                "extraction_stats": {
                    "total_sections": len(sections),
                    "sections_with_data": len([s for s in sections.values() if s.strip()]),
                    "missing_critical_fields": self._identify_missing_fields(sections)
                }
            }
            
            # Validate extracted metadata
            validation_result = self._validate_metadata(metadata)
            metadata["validation_result"] = validation_result
            
            logger.info(
                "Metadata extraction completed",
                scheme_id=scheme_id,
                nav_found=bool(metadata.get("nav_details", {}).get("current_nav")),
                expense_ratio_found=bool(metadata.get("financial_metrics", {}).get("expense_ratio")),
                risk_level=metadata.get("risk_info", {}).get("risk_level", "unknown")
            )
            
            return metadata
            
        except Exception as e:
            logger.error(
                "Metadata extraction failed",
                scheme_id=scheme_id,
                error=str(e)
            )
            raise
    
    def _extract_basic_info(self, sections: Dict[str, str]) -> Dict:
        """Extract basic fund information."""
        
        basic_info = {}
        
        # Extract scheme name from "About" or "Scheme Details" section
        scheme_name = self._extract_scheme_name(sections)
        if scheme_name:
            basic_info["scheme_name"] = scheme_name
        
        # Extract fund type
        fund_type = self._extract_fund_type(sections)
        if fund_type:
            basic_info["fund_type"] = fund_type
        
        # Extract launch date
        launch_date = self._extract_launch_date(sections)
        if launch_date:
            basic_info["launch_date"] = launch_date
        
        return basic_info
    
    def _extract_nav_details(self, sections: Dict[str, str]) -> Dict:
        """Extract NAV details from sections."""
        
        nav_details = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            # Try each NAV pattern
            for pattern in self.nav_patterns:
                matches = re.findall(pattern, section_text, re.IGNORECASE)
                if matches:
                    if "current" in pattern.lower() or "current nav" in pattern.lower():
                        nav_details["current_nav"] = self._parse_currency_value(matches[0])
                    elif "net asset value" in pattern.lower() or "nav" in pattern.lower():
                        nav_details["net_asset_value"] = self._parse_currency_value(matches[0])
                    else:
                        nav_details["nav"] = self._parse_currency_value(matches[0])
        
        # Extract NAV date if available
        nav_date = self._extract_nav_date(sections)
        if nav_date:
            nav_details["nav_date"] = nav_date
        
        return nav_details
    
    def _extract_financial_metrics(self, sections: Dict[str, str]) -> Dict:
        """Extract financial metrics like expense ratio, AUM, etc."""
        
        financial_metrics = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            # Extract expense ratio
            if "expense" in section_name.lower() or "ratio" in section_name.lower():
                expense_ratio = self._extract_percentage(section_text)
                if expense_ratio:
                    financial_metrics["expense_ratio"] = expense_ratio
            
            # Extract AUM
            if "aum" in section_text.lower() or "asset" in section_text.lower():
                aum = self._extract_aum(section_text)
                if aum:
                    financial_metrics["aum"] = aum
            
            # Extract fund size
            if "fund size" in section_text.lower():
                fund_size = self._extract_fund_size(section_text)
                if fund_size:
                    financial_metrics["fund_size"] = fund_size
        
        return financial_metrics
    
    def _extract_risk_info(self, sections: Dict[str, str]) -> Dict:
        """Extract risk information."""
        
        risk_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            # Try risk patterns
            for pattern in self.risk_patterns:
                matches = re.findall(pattern, section_text, re.IGNORECASE)
                if matches:
                    risk_level = matches[0].strip().upper()
                    risk_info["risk_level"] = risk_level
                    risk_info["risk_category"] = self._categorize_risk(risk_level)
                    break
        
        return risk_info
    
    def _extract_category_info(self, sections: Dict[str, str]) -> Dict:
        """Extract fund category information."""
        
        category_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            # Try category patterns
            for pattern in self.category_patterns:
                matches = re.findall(pattern, section_text, re.IGNORECASE)
                if matches:
                    category = matches[0].strip()
                    category_info["category"] = category
                    category_info["category_type"] = self._categorize_fund_type(category)
                    break
        
        return category_info
    
    def _extract_manager_info(self, sections: Dict[str, str]) -> Dict:
        """Extract fund manager information."""
        
        manager_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "manager" in section_name.lower():
                manager_info = self._extract_manager_details(section_text)
                break
        
        return manager_info
    
    def _extract_fund_house_info(self, sections: Dict[str, str]) -> Dict:
        """Extract fund house information."""
        
        fund_house_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "house" in section_name.lower() or "amc" in section_name.lower():
                fund_house_info = self._extract_amc_details(section_text)
                break
        
        return fund_house_info
    
    def _extract_description(self, sections: Dict[str, str]) -> str:
        """Extract fund description."""
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "about" in section_name.lower() or "description" in section_name.lower():
                # Clean up the description text
                description = re.sub(r'\s+', ' ', section_text.strip())
                return description[:500]  # Limit description length
        
        return ""
    
    def _extract_holdings(self, sections: Dict[str, str]) -> List[Dict]:
        """Extract portfolio holdings information."""
        
        holdings = []
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "holding" in section_name.lower() or "portfolio" in section_name.lower():
                # Parse holdings table/list
                holding_lines = [line.strip() for line in section_text.split('\n') if line.strip()]
                
                for line in holding_lines:
                    if self._is_holding_line(line):
                        holding = self._parse_holding_line(line)
                        if holding:
                            holdings.append(holding)
        
        return holdings
    
    def _extract_benchmark_info(self, sections: Dict[str, str]) -> Dict:
        """Extract benchmark information."""
        
        benchmark_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "benchmark" in section_name.lower():
                benchmark_info["benchmark"] = section_text.strip()[:200]
        
        return benchmark_info
    
    def _extract_returns_info(self, sections: Dict[str, str]) -> Dict:
        """Extract returns information."""
        
        returns_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "return" in section_name.lower():
                # Extract return percentages
                returns = self._extract_return_periods(section_text)
                if returns:
                    returns_info["returns"] = returns
        
        return returns_info
    
    def _extract_tax_info(self, sections: Dict[str, str]) -> Dict:
        """Extract tax information."""
        
        tax_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "tax" in section_name.lower():
                tax_info["tax_info"] = section_text.strip()[:300]
        
        return tax_info
    
    def _extract_min_investment_info(self, sections: Dict[str, str]) -> Dict:
        """Extract minimum investment information."""
        
        min_investment_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "minimum" in section_name.lower() or "min" in section_name.lower():
                min_investment_info = self._extract_min_amounts(section_text)
        
        return min_investment_info
    
    def _extract_exit_load_info(self, sections: Dict[str, str]) -> Dict:
        """Extract exit load information."""
        
        exit_load_info = {}
        
        for section_name, section_text in sections.items():
            if not section_text:
                continue
            
            if "exit" in section_name.lower() and "load" in section_name.lower():
                exit_load_info = self._extract_exit_load_details(section_text)
        
        return exit_load_info
    
    # Helper methods for specific extractions
    def _extract_scheme_name(self, sections: Dict[str, str]) -> str:
        """Extract scheme name from sections."""
        for section_name, section_text in sections.items():
            if section_name.lower() in ["scheme details", "about", "fund details"]:
                # Look for scheme name pattern
                patterns = [
                    r'([A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+Fund)',
                    r'([A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+)',
                    r'Scheme[:\s]*([A-Z\s&\s]+)'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, section_text, re.IGNORECASE)
                    if matches:
                        return matches[0].strip()
        return ""
    
    def _extract_fund_type(self, sections: Dict[str, str]) -> str:
        """Extract fund type from sections."""
        for section_name, section_text in sections.items():
            if "type" in section_name.lower() or "category" in section_name.lower():
                # Look for fund type indicators
                if "equity" in section_text.lower():
                    return "Equity"
                elif "debt" in section_text.lower():
                    return "Debt"
                elif "hybrid" in section_text.lower():
                    return "Hybrid"
                elif "elss" in section_text.lower():
                    return "ELSS"
        return ""
    
    def _extract_launch_date(self, sections: Dict[str, str]) -> str:
        """Extract fund launch date."""
        for section_name, section_text in sections.items():
            if "launch" in section_name.lower() or "inception" in section_name.lower():
                for pattern in self.date_patterns:
                    matches = re.findall(pattern, section_text)
                    if matches:
                        return matches[0]
        return ""
    
    def _extract_nav_date(self, sections: Dict[str, str]) -> str:
        """Extract NAV date."""
        for section_name, section_text in sections.items():
            if "nav" in section_name.lower():
                for pattern in self.date_patterns:
                    matches = re.findall(pattern, section_text)
                    if matches:
                        return matches[0]
        return ""
    
    def _parse_currency_value(self, value_str: str) -> Dict:
        """Parse currency value into amount and currency."""
        # Extract numeric value
        numeric_match = re.search(r'([\d,\.]+)', value_str)
        if not numeric_match:
            return {"amount": 0, "currency": "INR"}
        
        amount = float(numeric_match.group(1))
        
        # Determine currency
        if "₹" in value_str:
            currency = "INR"
        elif "cr" in value_str.lower():
            currency = "INR"
        elif "rs" in value_str.lower():
            currency = "INR"
        else:
            currency = "INR"
        
        return {"amount": amount, "currency": currency}
    
    def _extract_percentage(self, text: str) -> Optional[float]:
        """Extract percentage value from text."""
        for pattern in self.percentage_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[0])
                except ValueError:
                    continue
        return None
    
    def _extract_aum(self, text: str) -> Optional[Dict]:
        """Extract AUM from text."""
        for pattern in self.currency_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                parsed = self._parse_currency_value(matches[0])
                return parsed
        return None
    
    def _extract_fund_size(self, text: str) -> Optional[Dict]:
        """Extract fund size from text."""
        return self._extract_aum(text)
    
    def _categorize_risk(self, risk_level: str) -> str:
        """Categorize risk level."""
        risk_level = risk_level.upper()
        
        if risk_level in ["VERY LOW", "LOW"]:
            return "Low Risk"
        elif risk_level in ["MODERATE", "MEDIUM"]:
            return "Moderate Risk"
        elif risk_level in ["HIGH", "VERY HIGH"]:
            return "High Risk"
        else:
            return "Moderate Risk"
    
    def _categorize_fund_type(self, category: str) -> str:
        """Categorize fund type."""
        category = category.upper()
        
        if "EQUITY" in category:
            return "Equity Fund"
        elif "DEBT" in category:
            return "Debt Fund"
        elif "HYBRID" in category:
            return "Hybrid Fund"
        elif "ELSS" in category:
            return "ELSS Fund"
        else:
            return "Other Fund"
    
    def _extract_manager_details(self, text: str) -> Dict:
        """Extract manager details keeping only essential info."""
        manager_info = {}
        
        # Extract manager name
        name_patterns = [
            r'([A-Z]+\s+[A-Z]+\s+[A-Z]+)',  # Full name
            r'Mr\.?\s*([A-Z]+\s+[A-Z]+)',  # Mr. Name
            r'([A-Z]+\s+[A-Z]+)'  # Just name
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                manager_info["name"] = matches[0].strip()
                break
        
        # Extract tenure/experience
        tenure_patterns = [
            r'(\d+)\s*years?',
            r'Experience[:\s]*(\d+)\s*years?',
            r'Tenure[:\s]*(\d+)\s*years?'
        ]
        
        for pattern in tenure_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                manager_info["tenure_years"] = int(matches[0])
                break
        
        return manager_info
    
    def _extract_amc_details(self, text: str) -> Dict:
        """Extract AMC details keeping only essential info."""
        amc_info = {}
        
        # Extract AMC name
        amc_patterns = [
            r'([A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+Fund)',  # Full name
            r'([A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+)',  # Just name
        ]
        
        for pattern in amc_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                amc_info["name"] = matches[0].strip()
                break
        
        # Extract rank if available
        rank_match = re.search(r'Rank[:\s]*(\d+)', text, re.IGNORECASE)
        if rank_match:
            amc_info["rank"] = int(rank_match.group(1))
        
        # Extract AUM
        aum = self._extract_aum(text)
        if aum:
            amc_info["aum"] = aum
        
        return amc_info
    
    def _is_holding_line(self, line: str) -> bool:
        """Check if a line represents a holding."""
        # Simple heuristic: contains company name and percentage/amount
        return (
            bool(re.search(r'[A-Z]', line)) and  # Company name
            (bool(re.search(r'\d+\.?\d*%?', line)) or  # Percentage
             bool(re.search(r'[\d,\.]+', line)))  # Amount
        )
    
    def _parse_holding_line(self, line: str) -> Optional[Dict]:
        """Parse a holding line into structured data."""
        try:
            # Extract company name (first word(s))
            company_match = re.search(r'([A-Z\s&\s]+[A-Z\s&\s]+[A-Z\s&\s]+)', line)
            if not company_match:
                return None
            
            # Extract percentage or amount
            amount_match = re.search(r'(\d+\.?\d*%?)', line)
            if amount_match:
                percentage = float(amount_match.group(1))
            else:
                # Try to extract currency amount
                currency_match = re.search(r'([\d,\.]+)', line)
                if currency_match:
                    amount = float(currency_match.group(1))
                else:
                    return None
            
            return {
                "company": company_match.group(1).strip(),
                "percentage": percentage if 'percentage' in locals() else amount,
                "amount_type": "percentage" if 'percentage' in locals() else "amount"
            }
        except (ValueError, AttributeError):
            return None
    
    def _extract_return_periods(self, text: str) -> List[Dict]:
        """Extract return periods and percentages."""
        returns = []
        
        # Look for patterns like "1 year: 12.3%, 3 years: 15.6%"
        return_patterns = [
            r'(\d+)\s*years?[:\s]*([0-9.]+)%?',
            r'(\d+)\s*months?[:\s]*([0-9.]+)%?'
        ]
        
        for pattern in return_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                returns.append({
                    "period": match[0],
                    "period_unit": "years" if "year" in pattern else "months",
                    "return_percentage": float(match[1])
                })
        
        return returns
    
    def _extract_min_amounts(self, text: str) -> Dict:
        """Extract minimum investment amounts."""
        min_amounts = {}
        
        # Look for SIP and lumpsum amounts
        sip_match = re.search(r'SIP[:\s]*([₹\d,\.]+|\d+\.?\d*)', text, re.IGNORECASE)
        if sip_match:
            min_amounts["min_sip"] = self._parse_currency_value(sip_match.group(1))
        
        lumpsum_match = re.search(r'Lumpsum[:\s]*([₹\d,\.]+|\d+\.?\d*)', text, re.IGNORECASE)
        if lumpsum_match:
            min_amounts["min_lumpsum"] = self._parse_currency_value(lumpsum_match.group(1))
        
        # Generic minimum amount
        min_match = re.search(r'Minimum[:\s]*([₹\d,\.]+|\d+\.?\d*)', text, re.IGNORECASE)
        if min_match:
            min_amounts["min_amount"] = self._parse_currency_value(min_match.group(1))
        
        return min_amounts
    
    def _extract_exit_load_details(self, text: str) -> Dict:
        """Extract exit load details."""
        exit_load_info = {}
        
        # Look for exit load percentages and periods
        patterns = [
            r'(\d+\.?\d*)%\s*if\s*redeemed\s*within\s*(\d+)\s*years?',
            r'Exit Load[:\s]*(\d+\.?\d*)%',
            r'No\s*exit\s*load',
            r'Nil\s*exit\s*load'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if len(matches) == 3:  # Full pattern with period
                    exit_load_info["exit_load_percentage"] = float(matches[0])
                    exit_load_info["exit_load_period_years"] = int(matches[1])
                elif len(matches) == 1:  # Simple percentage
                    exit_load_info["exit_load_percentage"] = float(matches[0])
                elif "no" in matches[0].lower() or "nil" in matches[0].lower():
                    exit_load_info["exit_load"] = "No Exit Load"
                break
        
        return exit_load_info
    
    def _identify_missing_fields(self, sections: Dict[str, str]) -> List[str]:
        """Identify missing critical fields."""
        missing_fields = []
        
        # Check for critical sections
        critical_sections = ["Scheme Details", "Expense Ratio", "Exit Load", "Minimum Investment"]
        
        for section in critical_sections:
            if section not in sections or not sections.get(section, '').strip():
                missing_fields.append(section)
        
        return missing_fields
    
    def _validate_metadata(self, metadata: Dict) -> Dict:
        """Validate extracted metadata."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check for required fields
        if not metadata.get("basic_info", {}).get("scheme_name"):
            validation_result["errors"].append("Scheme name not found")
            validation_result["is_valid"] = False
        
        # Check for NAV data
        if not metadata.get("nav_details", {}):
            validation_result["warnings"].append("NAV details not found")
        
        # Check for financial metrics
        if not metadata.get("financial_metrics", {}).get("expense_ratio"):
            validation_result["warnings"].append("Expense ratio not found")
        
        # Validate data types
        try:
            if metadata.get("nav_details", {}).get("current_nav"):
                nav_amount = metadata["nav_details"]["current_nav"].get("amount", 0)
                if not isinstance(nav_amount, (int, float)):
                    validation_result["errors"].append("NAV amount should be numeric")
                    validation_result["is_valid"] = False
        except (KeyError, TypeError):
            validation_result["warnings"].append("NAV data format error")
        
        return validation_result
