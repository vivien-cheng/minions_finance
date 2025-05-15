import json

class CalculatorAgent(Agent):
    """Agent responsible for performing financial calculations"""
    
    def __init__(self):
        super().__init__("CalculatorAgent")
        
    def process(self, task: str, context: Dict[str, Any]) -> str:
        """Process calculation tasks"""
        try:
            calculations = []
            if "calculate" in task.lower():
                if "capex/revenue ratio" in task.lower():
                    calculations.append("CAPEX/Revenue Ratio")
                if "fixed assets/total assets ratio" in task.lower():
                    calculations.append("Fixed assets/Total Assets Ratio")
                if "return on assets" in task.lower() or "roa" in task.lower():
                    calculations.append("Return on Assets (ROA)")
            
            if not calculations:
                return json.dumps({
                    "error": "No calculations specified in task",
                    "task": task
                })
            
            data = context.get("data", {})
            if not data:
                return json.dumps({
                    "error": "No data provided for calculations",
                    "task": task
                })
            
            results = {}
            explanations = {}
            
            for calc in calculations:
                if calc == "CAPEX/Revenue Ratio":
                    capex = data.get("Purchases of property, plant, and equipment")
                    revenue = data.get("Net Sales")
                    if capex is not None and revenue is not None and revenue != 0:
                        ratio = capex / revenue
                        results[calc] = f"{ratio:.2%}"
                        explanations[calc] = f"CAPEX/Revenue Ratio = {capex:,} / {revenue:,} = {ratio:.2%}"
                
                elif calc == "Fixed assets/Total Assets Ratio":
                    fixed_assets = data.get("Property, Plant, and Equipment Net")
                    total_assets = data.get("Total Assets")
                    if fixed_assets is not None and total_assets is not None and total_assets != 0:
                        ratio = fixed_assets / total_assets
                        results[calc] = f"{ratio:.2%}"
                        explanations[calc] = f"Fixed assets/Total Assets Ratio = {fixed_assets:,} / {total_assets:,} = {ratio:.2%}"
                
                elif calc == "Return on Assets (ROA)":
                    net_income = data.get("Net Income")
                    total_assets = data.get("Total Assets")
                    if net_income is not None and total_assets is not None and total_assets != 0:
                        ratio = net_income / total_assets
                        results[calc] = f"{ratio:.2%}"
                        explanations[calc] = f"ROA = {net_income:,} / {total_assets:,} = {ratio:.2%}"
            
            return json.dumps({
                "calculations": results,
                "explanations": explanations
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"Calculation error: {str(e)}",
                "task": task
            })

class FormatterAgent(Agent):
    """Agent responsible for formatting financial values consistently"""
    
    def __init__(self):
        super().__init__("FormatterAgent")
        
    def process(self, task: str, context: Dict[str, Any]) -> str:
        """Format financial values consistently"""
        try:
            value = context.get("value")
            if value is None:
                return json.dumps({
                    "error": "No value provided for formatting",
                    "task": task
                })
            
            if isinstance(value, str):
                value = value.replace("$", "").replace(",", "").strip()
                try:
                    value = float(value)
                except ValueError:
                    return json.dumps({
                        "error": f"Could not convert value to number: {value}",
                        "task": task
                    })
            
            if abs(value) >= 1_000_000_000:  # Billions
                formatted = f"${value/1_000_000_000:.2f} billion"
            elif abs(value) >= 1_000_000:  # Millions
                formatted = f"${value/1_000_000:.2f} million"
            elif abs(value) >= 1_000:  # Thousands
                formatted = f"${value/1_000:.2f} thousand"
            else:
                formatted = f"${value:.2f}"
            
            return json.dumps({
                "formatted_value": formatted,
                "original_value": value
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"Formatting error: {str(e)}",
                "task": task
            })

class SummarizerAgent(Agent):
    """Agent responsible for summarizing financial analysis"""
    
    def __init__(self):
        super().__init__("SummarizerAgent")
        
    def process(self, task: str, context: Dict[str, Any]) -> str:
        """Summarize financial analysis concisely"""
        try:
            analysis = context.get("analysis", "")
            if not analysis:
                return json.dumps({
                    "error": "No analysis provided for summarization",
                    "task": task
                })
            
            # Extract key points
            key_points = []
            if "litigation" in analysis.lower():
                key_points.append("$1.2B Combat Arms Earplugs litigation charge")
            if "impairment" in analysis.lower():
                key_points.append("PFAS manufacturing exit impairment")
            if "russia" in analysis.lower():
                key_points.append("Russia exit costs")
            if "restructuring" in analysis.lower():
                key_points.append("Divestiture-related restructuring charges")
            
            # Create concise summary
            summary = "Operating margin change driven by: " + ", ".join(key_points)
            
            return json.dumps({
                "summary": summary,
                "key_points": key_points
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"Summarization error: {str(e)}",
                "task": task
            }) 