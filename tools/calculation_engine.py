import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def calculate(calculation_type: str, inputs: Dict[str, Any]) -> Dict:
    """
    Performs financial calculations based on provided inputs.
    """
    try:
        result = 0.0
        formula = ""
        steps = []
        
        if calculation_type == "pe_ratio":
            price = inputs.get("price", 0)
            eps = inputs.get("eps", 1)
            result = price / eps
            formula = "price / eps"
            steps = [f"{price} / {eps} = {result}"]
            
        elif calculation_type == "roe":
            net_income = inputs.get("net_income", 0)
            equity = inputs.get("equity", 1)
            result = net_income / equity
            formula = "net_income / shareholders_equity"
            steps = [f"{net_income} / {equity} = {result}"]

        elif calculation_type == "dcf":
            fcf_list = inputs.get("free_cash_flow", [])
            growth = inputs.get("growth_rate", 0.05)
            discount = inputs.get("discount_rate", 0.1)
            terminal = inputs.get("terminal_multiplier", 15)
            
            # Simple DCF implementation
            pv_fcf = 0
            for i, fcf in enumerate(fcf_list):
                pv = fcf / ((1 + discount) ** (i + 1))
                pv_fcf += pv
                steps.append(f"Year {i+1} PV: {pv}")
            
            terminal_value = (fcf_list[-1] * (1 + growth)) * terminal
            pv_terminal = terminal_value / ((1 + discount) ** len(fcf_list))
            result = pv_fcf + pv_terminal
            formula = "SUM(FCF / (1+r)^t) + (Terminal Value / (1+r)^n)"
            steps.append(f"PV of Terminal Value: {pv_terminal}")
            steps.append(f"Total Enterprise Value: {result}")

        elif calculation_type == "cagr":
            start = inputs.get("start_value", 1)
            end = inputs.get("end_value", 1)
            years = inputs.get("num_years", 1)
            result = (end / start) ** (1 / years) - 1
            formula = "(end / start) ^ (1 / years) - 1"
            steps = [f"({end} / {start}) ^ (1 / {years}) - 1 = {result}"]

        else:
            # Handle other ratios similarly
            val1 = inputs.get("numerator", 0)
            val2 = inputs.get("denominator", 1)
            result = val1 / val2
            formula = "numerator / denominator"
            steps = [f"{val1} / {val2} = {result}"]

        return {
            "calculation_type": calculation_type,
            "inputs_used": inputs,
            "result": round(float(result), 4),
            "intermediate_steps": steps,
            "interpretation": f"The calculated {calculation_type} is {round(result, 2)}.",
            "formula_used": formula
        }
    except Exception as e:
        logger.error(f"Calculation failed: {e}")
        return {"error": "calculation_failed", "reason": str(e)}
