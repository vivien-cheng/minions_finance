"""Calculator tool for performing financial calculations."""

from typing import Union, List, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
import math

class FinancialCalculator:
    """A calculator for performing financial calculations."""
    
    @staticmethod
    def calculate_percentage_change(initial: Union[float, Decimal], final: Union[float, Decimal]) -> float:
        """Calculate percentage change between two values.
        
        Args:
            initial: Initial value
            final: Final value
            
        Returns:
            Percentage change as a float
        """
        if initial == 0:
            return float('inf') if final > 0 else float('-inf')
        return ((final - initial) / abs(initial)) * 100
    
    @staticmethod
    def calculate_compound_interest(
        principal: Union[float, Decimal],
        rate: float,
        time: float,
        compounds_per_year: int = 1
    ) -> Decimal:
        """Calculate compound interest.
        
        Args:
            principal: Initial amount
            rate: Annual interest rate (as a decimal)
            time: Time in years
            compounds_per_year: Number of times interest is compounded per year
            
        Returns:
            Final amount after compound interest
        """
        principal = Decimal(str(principal))
        rate = Decimal(str(rate))
        time = Decimal(str(time))
        compounds = Decimal(str(compounds_per_year))
        
        amount = principal * (1 + rate/compounds) ** (compounds * time)
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_roi(
        initial_investment: Union[float, Decimal],
        final_value: Union[float, Decimal]
    ) -> float:
        """Calculate Return on Investment (ROI).
        
        Args:
            initial_investment: Initial investment amount
            final_value: Final value of investment
            
        Returns:
            ROI as a percentage
        """
        return FinancialCalculator.calculate_percentage_change(initial_investment, final_value)
    
    @staticmethod
    def calculate_annualized_return(
        initial_investment: Union[float, Decimal],
        final_value: Union[float, Decimal],
        years: float
    ) -> float:
        """Calculate annualized return.
        
        Args:
            initial_investment: Initial investment amount
            final_value: Final value of investment
            years: Number of years
            
        Returns:
            Annualized return as a percentage
        """
        if years <= 0:
            raise ValueError("Years must be positive")
            
        total_return = (final_value / initial_investment) - 1
        return ((1 + total_return) ** (1/years) - 1) * 100
    
    @staticmethod
    def calculate_present_value(
        future_value: Union[float, Decimal],
        rate: float,
        time: float
    ) -> Decimal:
        """Calculate present value.
        
        Args:
            future_value: Future value
            rate: Discount rate (as a decimal)
            time: Time in years
            
        Returns:
            Present value
        """
        future_value = Decimal(str(future_value))
        rate = Decimal(str(rate))
        time = Decimal(str(time))
        
        present_value = future_value / (1 + rate) ** time
        return present_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_future_value(
        present_value: Union[float, Decimal],
        rate: float,
        time: float
    ) -> Decimal:
        """Calculate future value.
        
        Args:
            present_value: Present value
            rate: Interest rate (as a decimal)
            time: Time in years
            
        Returns:
            Future value
        """
        present_value = Decimal(str(present_value))
        rate = Decimal(str(rate))
        time = Decimal(str(time))
        
        future_value = present_value * (1 + rate) ** time
        return future_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_loan_payment(
        principal: Union[float, Decimal],
        rate: float,
        years: int
    ) -> Decimal:
        """Calculate monthly loan payment.
        
        Args:
            principal: Loan amount
            rate: Annual interest rate (as a decimal)
            years: Loan term in years
            
        Returns:
            Monthly payment amount
        """
        principal = Decimal(str(principal))
        rate = Decimal(str(rate))
        months = Decimal(str(years * 12))
        
        # Monthly interest rate
        monthly_rate = rate / 12
        
        # Calculate monthly payment using the formula:
        # P = L[c(1 + c)^n]/[(1 + c)^n - 1]
        # where P = payment, L = loan amount, c = monthly interest rate, n = number of payments
        payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        return payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_amortization_schedule(
        principal: Union[float, Decimal],
        rate: float,
        years: int
    ) -> List[Dict[str, Any]]:
        """Calculate loan amortization schedule.
        
        Args:
            principal: Loan amount
            rate: Annual interest rate (as a decimal)
            years: Loan term in years
            
        Returns:
            List of dictionaries containing payment details for each period
        """
        monthly_payment = FinancialCalculator.calculate_loan_payment(principal, rate, years)
        balance = Decimal(str(principal))
        monthly_rate = Decimal(str(rate)) / 12
        schedule = []
        
        for month in range(1, years * 12 + 1):
            interest_payment = balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            balance -= principal_payment
            
            schedule.append({
                'month': month,
                'payment': monthly_payment,
                'principal': principal_payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'interest': interest_payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'balance': balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            })
            
        return schedule 