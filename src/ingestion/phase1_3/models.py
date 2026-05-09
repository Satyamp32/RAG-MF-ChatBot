"""
Data models for Phase 1.3 Structured Mutual Fund Metadata Extraction.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class NAVDetails(BaseModel):
    """NAV information extracted from fund data."""
    
    current_nav: Optional[Dict[str, float]] = None
    net_asset_value: Optional[Dict[str, float]] = None
    nav: Optional[Dict[str, float]] = None
    nav_date: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FinancialMetrics(BaseModel):
    """Financial metrics extracted from fund data."""
    
    expense_ratio: Optional[float] = None
    aum: Optional[Dict[str, float]] = None
    fund_size: Optional[Dict[str, float]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RiskInfo(BaseModel):
    """Risk information extracted from fund data."""
    
    risk_level: Optional[str] = None
    risk_category: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CategoryInfo(BaseModel):
    """Category information extracted from fund data."""
    
    category: Optional[str] = None
    category_type: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ManagerInfo(BaseModel):
    """Fund manager information extracted from fund data."""
    
    name: Optional[str] = None
    tenure_years: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FundHouseInfo(BaseModel):
    """Fund house information extracted from fund data."""
    
    name: Optional[str] = None
    rank: Optional[int] = None
    aum: Optional[Dict[str, float]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Holding(BaseModel):
    """Portfolio holding information."""
    
    company: str
    percentage: Optional[float] = None
    amount_type: str  # "percentage" or "amount"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BenchmarkInfo(BaseModel):
    """Benchmark information extracted from fund data."""
    
    benchmark: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReturnsInfo(BaseModel):
    """Returns information extracted from fund data."""
    
    returns: List[Dict[str, float]] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaxInfo(BaseModel):
    """Tax information extracted from fund data."""
    
    tax_info: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MinInvestmentInfo(BaseModel):
    """Minimum investment information extracted from fund data."""
    
    min_sip: Optional[Dict[str, float]] = None
    min_lumpsum: Optional[Dict[str, float]] = None
    min_amount: Optional[Dict[str, float]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExitLoadInfo(BaseModel):
    """Exit load information extracted from fund data."""
    
    exit_load_percentage: Optional[float] = None
    exit_load_period_years: Optional[int] = None
    exit_load: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MutualFundMetadata(BaseModel):
    """Complete structured metadata for a mutual fund."""
    
    scheme_id: str
    source_url: str
    fetched_at: datetime
    extraction_health: str = "ok"
    basic_info: Dict[str, str]
    nav_details: NAVDetails
    financial_metrics: FinancialMetrics
    risk_info: RiskInfo
    category_info: CategoryInfo
    manager_info: ManagerInfo
    fund_house_info: FundHouseInfo
    description: Optional[str] = None
    holdings: List[Holding] = []
    benchmark_info: BenchmarkInfo
    returns_info: ReturnsInfo
    tax_info: TaxInfo
    min_investment_info: MinInvestmentInfo
    exit_load_info: ExitLoadInfo
    extraction_stats: Dict[str, int]
    validation_result: Dict[str, Union[str, List[str]]]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExtractionStats(BaseModel):
    """Statistics for metadata extraction."""
    
    total_sections: int
    sections_with_data: int
    missing_critical_fields: List[str]
    extraction_time: Optional[float] = None
    nav_extraction_success: bool
    expense_ratio_extraction_success: bool
    risk_level_extraction_success: bool
    category_extraction_success: bool
    manager_extraction_success: bool
    fund_house_extraction_success: bool
    holdings_extraction_success: bool
    benchmark_extraction_success: bool
    returns_extraction_success: bool
    tax_extraction_success: bool
    min_investment_extraction_success: bool
    exit_load_extraction_success: bool
