"""
Cost Estimation Module for Trade Data AI Analyzer
Calculates estimated and actual API costs based on token usage
"""

import math
import logging
from typing import Dict, Optional
from dataclasses import dataclass

try:
    import tiktoken
except ImportError:
    tiktoken = None
    
logger = logging.getLogger(__name__)


@dataclass
class CostConfig:
    # Claude Sonnet 4.6
    SONNET_4_6_INPUT_RATE: float = 3.00
    SONNET_4_6_OUTPUT_RATE: float = 15.00
    
    # Claude Opus 4.6
    OPUS_4_6_INPUT_RATE: float = 5.00
    OPUS_4_6_OUTPUT_RATE: float = 25.00
    
    # Claude Haiku 3
    HAIKU_3_INPUT_RATE: float = 0.25
    HAIKU_3_OUTPUT_RATE: float = 1.25
    
    # Exchange rate
    USD_TO_INR: float = 92.0


class CostEstimator:
    """Estimates and tracks API costs for trade data analysis"""
    
    def __init__(self):
        self.config = CostConfig()
        
        # Default token assumptions
        self.TOKENS_PER_DESCRIPTION = 100      # Average tokens per product description
        self.TOKENS_PER_OUTPUT_CELL = 8        # Average tokens per output cell
        self.SYSTEM_INSTRUCTION_TOKENS = 500   # One-time system instruction tokens
        
        # Conversion factor: ~4 characters per token
        self.CHARS_PER_TOKEN = 4
    
    def estimate_tokens_from_text(self, text: str) -> int:
        """Estimate tokens from text using tiktoken or fallback heuristic"""
        if not text:
            return 0
            
        text_str = str(text).strip()
        
        if tiktoken:
            try:
                # cl100k_base is the most common modern tokenizer (GPT-4, Claude approximations)
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text_str))
            except Exception as e:
                logger.warning(f"Tiktoken error: {e}, falling back to heuristic")
                
        # Fallback to length heuristic
        return max(1, len(text_str) // self.CHARS_PER_TOKEN)
    
    def estimate_pre_analysis(
        self,
        row_count: int,
        column_count: int,
        avg_description_length: Optional[int] = None,
        model: str = "flash"
    ) -> Dict:
        """
        Estimate costs BEFORE running analysis
        
        Args:
            row_count: Number of rows to analyze
            column_count: Number of output columns
            avg_description_length: Average length of product descriptions (in characters)
            model: "flash" or "pro"
            
        Returns:
            Dictionary with cost estimation details
        """
        # Calculate input tokens
        tokens_per_desc = self.TOKENS_PER_DESCRIPTION
        if avg_description_length:
            tokens_per_desc = max(20, avg_description_length // self.CHARS_PER_TOKEN)
        
        total_input_tokens = (
            self.SYSTEM_INSTRUCTION_TOKENS +  # System instruction (once)
            (row_count * tokens_per_desc)      # All descriptions
        )
        
        # Calculate output tokens
        total_output_tokens = row_count * column_count * self.TOKENS_PER_OUTPUT_CELL
        
        # Get rates based on model
        if model == "claude-sonnet-4.6":
            input_rate = self.config.SONNET_4_6_INPUT_RATE
            output_rate = self.config.SONNET_4_6_OUTPUT_RATE
        elif model == "claude-opus-4.6":
            input_rate = self.config.OPUS_4_6_INPUT_RATE
            output_rate = self.config.OPUS_4_6_OUTPUT_RATE
        else: # default to haiku-3
            input_rate = self.config.HAIKU_3_INPUT_RATE
            output_rate = self.config.HAIKU_3_OUTPUT_RATE
        
        # Calculate costs in USD
        input_cost_usd = (total_input_tokens / 1_000_000) * input_rate
        output_cost_usd = (total_output_tokens / 1_000_000) * output_rate
        total_cost_usd = input_cost_usd + output_cost_usd
        
        # Convert to INR
        input_cost_inr = input_cost_usd * self.config.USD_TO_INR
        output_cost_inr = output_cost_usd * self.config.USD_TO_INR
        total_cost_inr = total_cost_usd * self.config.USD_TO_INR
        
        return {
            "type": "estimate",
            "model": model,
            "row_count": row_count,
            "column_count": column_count,
            "tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_input_tokens + total_output_tokens
            },
            "cost_usd": {
                "input": round(input_cost_usd, 4),
                "output": round(output_cost_usd, 4),
                "total": round(total_cost_usd, 4)
            },
            "cost_inr": {
                "input": round(input_cost_inr, 2),
                "output": round(output_cost_inr, 2),
                "total": round(total_cost_inr, 2)
            },
            "rates": {
                "input_per_million": input_rate,
                "output_per_million": output_rate,
                "exchange_rate": self.config.USD_TO_INR
            }
        }
    
    def calculate_actual_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "flash"
    ) -> Dict:
        """
        Calculate actual costs based on real token usage
        
        Args:
            input_tokens: Actual input tokens used
            output_tokens: Actual output tokens used
            model: "flash" or "pro"
            
        Returns:
            Dictionary with actual cost details
        """
        # Get rates based on model
        if model == "claude-sonnet-4.6":
            input_rate = self.config.SONNET_4_6_INPUT_RATE
            output_rate = self.config.SONNET_4_6_OUTPUT_RATE
        elif model == "claude-opus-4.6":
            input_rate = self.config.OPUS_4_6_INPUT_RATE
            output_rate = self.config.OPUS_4_6_OUTPUT_RATE
        else: # default to haiku-3
            input_rate = self.config.HAIKU_3_INPUT_RATE
            output_rate = self.config.HAIKU_3_OUTPUT_RATE
        
        # Calculate costs in USD
        input_cost_usd = (input_tokens / 1_000_000) * input_rate
        output_cost_usd = (output_tokens / 1_000_000) * output_rate
        total_cost_usd = input_cost_usd + output_cost_usd
        
        # Convert to INR
        total_cost_inr = total_cost_usd * self.config.USD_TO_INR
        
        return {
            "type": "actual",
            "model": model,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            },
            "cost_usd": {
                "input": round(input_cost_usd, 4),
                "output": round(output_cost_usd, 4),
                "total": round(total_cost_usd, 4)
            },
            "cost_inr": {
                "input": round(input_cost_usd * self.config.USD_TO_INR, 2),
                "output": round(output_cost_usd * self.config.USD_TO_INR, 2),
                "total": round(total_cost_inr, 2)
            }
        }
    
    def estimate_from_descriptions(
        self,
        descriptions: list,
        column_count: int,
        model: str = "flash"
    ) -> Dict:
        """
        Estimate costs based on actual description texts
        
        Args:
            descriptions: List of product description strings
            column_count: Number of output columns
            model: "flash" or "pro"
            
        Returns:
            Dictionary with detailed cost estimation
        """
        if not descriptions:
            return self.estimate_pre_analysis(0, column_count, model=model)
        
        # Calculate actual tokens from descriptions
        total_desc_tokens = sum(self.estimate_tokens_from_text(desc) for desc in descriptions)
        avg_tokens = total_desc_tokens // len(descriptions) if descriptions else 0
        
        # Use actual measurements
        total_input_tokens = self.SYSTEM_INSTRUCTION_TOKENS + total_desc_tokens
        total_output_tokens = len(descriptions) * column_count * self.TOKENS_PER_OUTPUT_CELL
        
        # Get rates
        if model == "claude-sonnet-4.6":
            input_rate = self.config.SONNET_4_6_INPUT_RATE
            output_rate = self.config.SONNET_4_6_OUTPUT_RATE
        elif model == "claude-opus-4.6":
            input_rate = self.config.OPUS_4_6_INPUT_RATE
            output_rate = self.config.OPUS_4_6_OUTPUT_RATE
        else: # default to haiku-3
            input_rate = self.config.HAIKU_3_INPUT_RATE
            output_rate = self.config.HAIKU_3_OUTPUT_RATE
        
        # Calculate costs
        input_cost_usd = (total_input_tokens / 1_000_000) * input_rate
        output_cost_usd = (total_output_tokens / 1_000_000) * output_rate
        total_cost_usd = input_cost_usd + output_cost_usd
        total_cost_inr = total_cost_usd * self.config.USD_TO_INR
        
        return {
            "type": "estimate_detailed",
            "model": model,
            "row_count": len(descriptions),
            "column_count": column_count,
            "avg_tokens_per_row": avg_tokens,
            "tokens": {
                "system_instruction": self.SYSTEM_INSTRUCTION_TOKENS,
                "descriptions": total_desc_tokens,
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_input_tokens + total_output_tokens
            },
            "cost_usd": {
                "input": round(input_cost_usd, 4),
                "output": round(output_cost_usd, 4),
                "total": round(total_cost_usd, 4)
            },
            "cost_inr": {
                "input": round(input_cost_usd * self.config.USD_TO_INR, 2),
                "output": round(output_cost_usd * self.config.USD_TO_INR, 2),
                "total": round(total_cost_inr, 2)
            }
        }
    
    def update_rates(self, flash_input: float = None, flash_output: float = None,
                     pro_input: float = None, pro_output: float = None,
                     exchange_rate: float = None):
        """Update pricing rates"""
        if flash_input:
            self.config.FLASH_INPUT_RATE = flash_input
        if flash_output:
            self.config.FLASH_OUTPUT_RATE = flash_output
        if pro_input:
            self.config.PRO_INPUT_RATE = pro_input
        if pro_output:
            self.config.PRO_OUTPUT_RATE = pro_output
        if exchange_rate:
            self.config.USD_TO_INR = exchange_rate


# Create singleton instance
cost_estimator = CostEstimator()


if __name__ == "__main__":
    # Test the estimator
    estimator = CostEstimator()
    
    # Test pre-analysis estimate
    estimate = estimator.estimate_pre_analysis(
        row_count=1500,
        column_count=3,
        model="flash"
    )
    
    print("Pre-Analysis Estimate (1500 rows, 3 columns):")
    print(f"  Input Tokens: {estimate['tokens']['input']:,}")
    print(f"  Output Tokens: {estimate['tokens']['output']:,}")
    print(f"  Total Tokens: {estimate['tokens']['total']:,}")
    print(f"  Estimated Cost: ${estimate['cost_usd']['total']:.4f} (₹{estimate['cost_inr']['total']:.2f})")
