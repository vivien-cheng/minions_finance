"""Utility functions for financial data extraction and analysis."""

import re
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

def extract_monetary_values(text: str) -> List[Tuple[str, Decimal]]:
    """Extract monetary values from text.
    
    Args:
        text: Text to extract monetary values from
        
    Returns:
        List of tuples containing (value, amount)
    """
    # Pattern for monetary values (e.g., $1,234.56, 1,234.56 million)
    pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|trillion)?'
    
    matches = re.finditer(pattern, text)
    values = []
    
    for match in matches:
        amount = Decimal(match.group(1).replace(',', ''))
        unit = match.group(2)
        
        if unit == 'million':
            amount *= Decimal('1000000')
        elif unit == 'billion':
            amount *= Decimal('1000000000')
        elif unit == 'trillion':
            amount *= Decimal('1000000000000')
            
        values.append((match.group(0), amount))
    
    return values

def extract_percentages(text: str) -> List[Tuple[str, float]]:
    """Extract percentage values from text.
    
    Args:
        text: Text to extract percentages from
        
    Returns:
        List of tuples containing (value, percentage)
    """
    # Pattern for percentages (e.g., 12.34%, 12.34 percent)
    pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:%|percent|percentage)'
    
    matches = re.finditer(pattern, text)
    percentages = []
    
    for match in matches:
        value = float(match.group(1).replace(',', ''))
        percentages.append((match.group(0), value))
    
    return percentages

def extract_dates(text: str) -> List[Tuple[str, str]]:
    """Extract dates from text.
    
    Args:
        text: Text to extract dates from
        
    Returns:
        List of tuples containing (value, formatted_date)
    """
    # Pattern for dates (e.g., January 1, 2023, 01/01/2023)
    patterns = [
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4}',
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}'
    ]
    
    dates = []
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            dates.append((match.group(0), match.group(0)))
    
    return dates

def check_financial_terms(text: str, terms: List[str]) -> Dict[str, bool]:
    """Check for presence of financial terms in text.
    
    Args:
        text: Text to check
        terms: List of terms to look for
        
    Returns:
        Dictionary mapping terms to their presence (True/False)
    """
    return {term: term.lower() in text.lower() for term in terms}

def extract_financial_metrics(text: str) -> Dict[str, Any]:
    """Extract various financial metrics from text.
    
    Args:
        text: Text to extract metrics from
        
    Returns:
        Dictionary containing extracted metrics
    """
    metrics = {
        'monetary_values': extract_monetary_values(text),
        'percentages': extract_percentages(text),
        'dates': extract_dates(text),
        'common_terms': check_financial_terms(text, [
            'revenue', 'profit', 'loss', 'income', 'expense',
            'assets', 'liabilities', 'equity', 'cash flow',
            'earnings', 'dividend', 'stock', 'share'
        ])
    }
    
    return metrics