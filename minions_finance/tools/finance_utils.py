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

def retrieve_financial_context(text: str, query: str) -> List[Tuple[str, float]]:
    """Retrieve relevant financial context based on semantic similarity and financial relevance.
    
    Args:
        text: The full text to search in
        query: The search query
        
    Returns:
        List of tuples containing (context_snippet, relevance_score)
    """
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Define financial keywords and their weights
    financial_keywords = {
        'revenue': 2.0,
        'income': 2.0,
        'expense': 2.0,
        'profit': 2.0,
        'loss': 2.0,
        'asset': 1.5,
        'liability': 1.5,
        'equity': 1.5,
        'cash': 1.5,
        'debt': 1.5,
        'ratio': 1.5,
        'margin': 1.5,
        'growth': 1.5,
        'decline': 1.5,
        'increase': 1.5,
        'decrease': 1.5,
        'million': 1.0,
        'billion': 1.0,
        'percent': 1.0,
        '%': 1.0,
        '$': 1.0
    }
    
    # Score each sentence based on:
    # 1. Presence of financial keywords
    # 2. Presence of numbers
    # 3. Semantic similarity to query
    scored_sentences = []
    for sentence in sentences:
        score = 0.0
        
        # Check for financial keywords
        for keyword, weight in financial_keywords.items():
            if keyword.lower() in sentence.lower():
                score += weight
        
        # Check for numbers (financial data)
        if re.search(r'\d+(?:,\d{3})*(?:\.\d+)?', sentence):
            score += 1.0
            
        # Check for currency symbols
        if '$' in sentence:
            score += 0.5
            
        # Check for percentages
        if '%' in sentence or 'percent' in sentence.lower():
            score += 0.5
            
        # Check for financial statement sections
        if any(section in sentence.lower() for section in ['income statement', 'balance sheet', 'cash flow', 'financial statement']):
            score += 1.0
            
        # Check for temporal indicators (important for financial analysis)
        if any(term in sentence.lower() for term in ['year', 'quarter', 'month', 'period', 'fiscal']):
            score += 0.5
            
        scored_sentences.append((sentence, score))
    
    # Sort by score and return top results
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    return scored_sentences[:5]  # Return top 5 most relevant sentences

def extract_financial_metrics(text: str) -> Dict[str, List[Tuple[str, float]]]:
    """Extract financial metrics from text.
    
    Args:
        text: Text to extract metrics from
        
    Returns:
        Dictionary mapping metric types to lists of (value, confidence) tuples
    """
    metrics = {
        'monetary_values': [],
        'percentages': [],
        'ratios': [],
        'dates': []
    }
    
    # Extract monetary values
    monetary_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:million|billion|trillion)?'
    for match in re.finditer(monetary_pattern, text):
        value = float(match.group(1).replace(',', ''))
        metrics['monetary_values'].append((match.group(0), 1.0))
    
    # Extract percentages
    percentage_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:%|percent|percentage)'
    for match in re.finditer(percentage_pattern, text):
        value = float(match.group(1).replace(',', ''))
        metrics['percentages'].append((match.group(0), 1.0))
    
    # Extract ratios
    ratio_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*:\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
    for match in re.finditer(ratio_pattern, text):
        metrics['ratios'].append((match.group(0), 1.0))
    
    # Extract dates
    date_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4}'
    for match in re.finditer(date_pattern, text):
        metrics['dates'].append((match.group(0), 1.0))
    
    return metrics