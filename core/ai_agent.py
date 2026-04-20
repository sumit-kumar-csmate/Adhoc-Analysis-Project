"""
AI Agent for analyzing trade data using Claude API
Material-specific classification with structured output parsing
Uses claude-sonnet-4-5 via the claude.opuscode.pro proxy as primary model
Falls back to Gemini proxy if Claude is unavailable
"""

import os
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradeDataAgent:
    """AI Agent for material-specific trade data classification"""
    
    def __init__(self, config_path: str = "config/materials_config.json"):
        """Initialize the agent with materials configuration"""
        api_key = os.getenv("CLAUDE_API_KEY", os.getenv("OPENAI_API_KEY"))
        base_url = os.getenv("CLAUDE_BASE_URL", "https://claude.opuscode.pro/api/v1")

        if not api_key:
            raise ValueError("No API key found. Set CLAUDE_API_KEY in environment variables.")

        # Claude client (used for both classification and prompt enhancement)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = "claude-haiku-3"  # Default; overridden per-request by flask_app
        logger.info(f"Claude client configured: {base_url} (model: {self.model_name})")

        self.system_instruction = None
        
        # Load materials configuration
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.materials_config = config['materials']
        
        self.current_material = None
        logger.info(f"Agent initialized with {len(self.materials_config)} materials")
    
    def reload_materials_config(self):
        """Reload materials configuration from file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.materials_config = config['materials']
            logger.info(f"Materials config reloaded: {len(self.materials_config)} materials")
        except Exception as e:
            logger.error(f"Failed to reload materials config: {e}")
    
    def _extract_system_instruction(self, prompt_template: str) -> str:
        """
        Extract system instruction from prompt template.
        Removes {description} and {input_data} placeholders and focuses on the instructions.
        """
        # Remove the actual execution/input request parts
        instruction = prompt_template
        
        # Remove common input request patterns
        patterns_to_remove = [
            r'Now, process the following input.*',
            r'Begin your analysis of.*',
            r'Input Description:.*',
            r'Input Data:.*',
            r'\{description\}',
            r'\{input_data\}'
        ]
        
        for pattern in patterns_to_remove:
            instruction = re.sub(pattern, '', instruction, flags=re.DOTALL | re.IGNORECASE)
        
        # Enforce strict JSON output
        instruction += "\n\nCRITICAL: Output ONLY valid JSON. No markdown code blocks, no explanations, no prologue. Start with { and end with }."
        
        return instruction.strip()
    
    def set_material(self, material_name: str):
        """Set the current material for classification and create model with system instructions"""
        # Reload config to get latest materials
        self.reload_materials_config()
        
        if material_name not in self.materials_config:
            raise ValueError(f"Material '{material_name}' not found in configuration")
        
        self.current_material = material_name
        
        # Get material config
        material_config = self.materials_config[material_name]
        raw_template = material_config['prompt_template']
        
        # Store system instruction for the current material
        self.system_instruction = self._extract_system_instruction(raw_template)
        logger.info(f"System instruction set for material: {material_name}")
        
        logger.info(f"Agent switched to material: {material_name}")
    
    def get_available_materials(self) -> List[str]:
        """Get list of available materials (reloads config to get latest)"""
        # Always reload to ensure fresh data
        self.reload_materials_config()
        return list(self.materials_config.keys())
    
    def classify_description(self, description: str, retries: int = 3, mode: str = 'specific') -> Dict[str, str]:
        """
        Classify a product description using the selected mode.
        Args:
            description: Product description to analyze
            retries: Number of retry attempts
            mode: 'specific' (filter) or 'universal' (discovery)
        """
        if not description or description.strip() == "":
            return self._empty_classification()

        # UNIVERSAL MODE (DISCOVERY)
        if mode == 'universal':
            current_system_instruction = """
Act as a Senior Trade Analyst. Analyze product descriptions and identify what the product is.

Extract the following fields:
1. material_name: The common commercial name of the product (e.g., "Tomato Paste", "Steel Coil", "Polyethylene").
2. grade: Quality or technical grade (e.g., "Industrial", "Food Grade", "304L").
3. manufacturer: The producer name if available.
4. key_specifications: A summary of the most important technical specs found (e.g., "Brix 36-38%", "Thickness 2mm").
5. category: A high-level category (e.g., "Chemicals", "Metals", "Food").

If the input is garbage or empty, return "N/A" for all fields.

CRITICAL: Output ONLY valid JSON. No markdown code blocks, no explanations, no prologue. Start with { and end with }.
"""
            expected_keys = {'material_name', 'grade', 'manufacturer', 'key_specifications', 'category'}

        # SPECIFIC MODE (FILTER)
        else:
            if not self.current_material:
                raise ValueError("No material selected for specific mode.")
            
            current_system_instruction = self.system_instruction
            
            if not current_system_instruction:
                raise ValueError("System instruction not initialized. Call set_material() first.")
            
            # Get expected categories
            material_config = self.materials_config[self.current_material]
            categories = material_config.get('classification_categories', [])
            expected_keys = {self._category_to_key(cat) for cat in categories}

        # API Call
        for attempt in range(retries):
            try:
                
                # Call Claude for classification
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": current_system_instruction},
                        {"role": "user", "content": description}
                    ],
                    temperature=0.1,
                    max_tokens=1024
                )
                
                # Parse JSON
                result_text = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
                try:
                    classification = json.loads(result_text)
                except json.JSONDecodeError as e:
                     logger.warning(f"JSON Parse Error (Attempt {attempt+1}): {e}")
                     logger.warning(f"Raw Response Text: '{result_text}'")
                     
                     # Retry on malformed JSON
                     if attempt < retries - 1:
                         time.sleep(2) # brief pause before retry
                         continue
                     raise ValueError(f"Invalid JSON response: {result_text[:50]}...")
                
                # Extract Token Usage
                usage = getattr(response, 'usage', None)
                if usage:
                    classification["_prompt_tokens"] = getattr(usage, 'prompt_tokens', 0)
                    classification["_completion_tokens"] = getattr(usage, 'completion_tokens', 0)
                else:
                    classification["_prompt_tokens"] = 0
                    classification["_completion_tokens"] = 0

                # Universal Mode Return
                if mode == 'universal':
                    return classification

                # Specific Mode Return
                if classification.get("material_type") == "Others":
                    others_dict = {k: "Others" for k in expected_keys}
                    others_dict["_prompt_tokens"] = classification["_prompt_tokens"]
                    others_dict["_completion_tokens"] = classification["_completion_tokens"]
                    return others_dict
                
                # Validate Specific Mode Keys
                if not expected_keys.issubset(classification.keys()):
                    for key in expected_keys:
                        if key not in classification:
                            classification[key] = "N/A"
                            
                return classification

            except Exception as e:
                error_str = str(e)
                logger.error(f"API call error (attempt {attempt + 1}): {e}")
                
                # specific handling for 429 Resource Exhausted
                if "429" in error_str or "quota" in error_str.lower():
                    wait_time = 60 * (attempt + 1)  # Exponential backoff: 60s, 120s...
                    logger.warning(f"Quota exceeded. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                
                if attempt == retries - 1:
                     return {k: "Error" for k in expected_keys} if mode == 'specific' else {"error": str(e)}
                
                # Default backoff for other errors
                time.sleep(2 * (attempt + 1))
        
        return {}

    
    def _category_to_key(self, category: str) -> str:
        """Convert category name to JSON key format"""
        return category.lower().replace(' ', '_').replace('-', '_')
    
    def get_classification_categories(self) -> List[str]:
        """Get classification categories for current material"""
        if not self.current_material:
            return []
        return self.materials_config[self.current_material].get('classification_categories', [])
    
    def _classify_chunk(self, chunk: List[str], start_idx: int, mode: str, retries: int = 3) -> Dict[int, Dict]:
        """
        Send a batch of descriptions in ONE API call and return a dict of {original_index: result}.
        Uses numbered JSON array format so Claude returns all results at once.
        """
        if mode == 'universal':
            system_instruction = """Act as a Senior Trade Analyst. Analyze product descriptions and identify what each product is.

You will receive a numbered list of descriptions. For EACH item return a JSON object with:
- material_name, grade, manufacturer, key_specifications, category

Return a JSON ARRAY with one object per input, in the same order.
CRITICAL: Output ONLY a valid JSON array [...]. No markdown, no explanation."""

        else:
            if not self.system_instruction:
                raise ValueError("System instruction not initialized. Call set_material() first.")
            # Strip the single-object footer that conflicts with array output
            base = re.sub(
                r'CRITICAL:\s*Output ONLY valid JSON.*Start with \{.*?\}\.',
                '',
                self.system_instruction,
                flags=re.DOTALL | re.IGNORECASE
            ).rstrip()
            system_instruction = base + """

You will receive a NUMBERED LIST of product descriptions (e.g. "1. desc...\n2. desc...").
For EACH numbered item, produce one result object using the same JSON keys as above.
Return ALL results as a single JSON ARRAY in the same order as the input.

Example output format (3 items):
[
  { "key1": "val", "key2": "val" },
  { "key1": "val", "key2": "val" },
  { "key1": "val", "key2": "val" }
]

CRITICAL: Output ONLY the JSON array. Start with [ and end with ]. No markdown, no explanation, no extra text."""

        # Build numbered input
        numbered_input = "\n".join(f"{i+1}. {desc}" for i, desc in enumerate(chunk))

        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": numbered_input}
                    ],
                    temperature=0.1,
                    max_tokens=4096  # Max output for Haiku
                )

                # Extract Token Usage for the chunk
                usage = getattr(response, 'usage', None)
                chunk_prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
                chunk_completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0

                raw = response.choices[0].message.content
                logger.info(f"_classify_chunk RAW response (chunk start={start_idx}, len={len(chunk)}): {raw[:500]!r}")
                raw = raw.replace('```json', '').replace('```', '').strip()

                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError(f"Expected JSON array, got: {type(parsed)}")
                    
                # Distribute tokens evenly among parsed items
                parsed_count = max(1, len([i for i in parsed if i]))
                avg_prompt = chunk_prompt_tokens // parsed_count
                avg_completion = chunk_completion_tokens // parsed_count

                # Map back to original indices — normalise keys to lowercase for consistent lookup
                result_map = {}
                for i, item in enumerate(parsed):
                    if i < len(chunk):
                        # Normalise all keys to lowercase so lookups always work
                        normalised = {k.lower().replace(' ', '_').replace('-', '_'): v for k, v in item.items()}
                        # Also keep original keys
                        normalised.update(item)
                        
                        # Add usage metadata
                        normalised["_prompt_tokens"] = avg_prompt
                        normalised["_completion_tokens"] = avg_completion
                        
                        result_map[start_idx + i] = normalised
                # Fill any missing items
                for i in range(len(chunk)):
                    if (start_idx + i) not in result_map:
                        result_map[start_idx + i] = {"_prompt_tokens": 0, "_completion_tokens": 0}
                return result_map

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"_classify_chunk parse error (attempt {attempt+1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                # On final failure fall back to individual calls
                logger.warning("Chunk parse failed after retries, falling back to per-item calls")
                result_map = {}
                for i, desc in enumerate(chunk):
                    result_map[start_idx + i] = self.classify_description(desc, mode=mode)
                return result_map

            except Exception as e:
                error_str = str(e)
                logger.error(f"_classify_chunk API error (attempt {attempt+1}): {e}")
                if "429" in error_str or "quota" in error_str.lower():
                    time.sleep(60 * (attempt + 1))
                    continue
                if attempt == retries - 1:
                    result_map = {}
                    for i in range(len(chunk)):
                        result_map[start_idx + i] = {}
                    return result_map
                time.sleep(2 * (attempt + 1))

        return {}

    def classify_batch(self, descriptions: List[str], progress_callback=None,
                       chunk_size: int = 25, max_workers: int = 5,
                       mode: str = 'specific') -> List[Dict[str, str]]:
        """
        Classify multiple descriptions by batching them into chunk_size groups,
        sending each chunk as ONE API call, and running chunks concurrently.

        500 descriptions with chunk_size=25 = 20 API calls (vs 500 before).

        Args:
            descriptions: List of product descriptions
            progress_callback: Optional callback(completed, total)
            chunk_size: Descriptions per API call (default 25)
            max_workers: Concurrent chunk requests (default 5)
            mode: 'specific' or 'universal'

        Returns:
            List of classification dicts in original order
        """
        total = len(descriptions)
        results = [{}] * total
        completed = 0

        # Split into chunks
        chunks = [
            (descriptions[i:i + chunk_size], i)
            for i in range(0, total, chunk_size)
        ]

        logger.info(f"classify_batch: {total} items → {len(chunks)} chunks of ≤{chunk_size}, {max_workers} concurrent")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(self._classify_chunk, chunk, start, mode): (chunk, start)
                for chunk, start in chunks
            }

            for future in as_completed(future_to_chunk):
                chunk, start = future_to_chunk[future]
                try:
                    result_map = future.result()
                    for idx, res in result_map.items():
                        results[idx] = res
                    completed += len(chunk)
                except Exception as e:
                    logger.error(f"Chunk starting at {start} failed: {e}")
                    completed += len(chunk)

                if progress_callback:
                    progress_callback(min(completed, total), total)

        return results
    
    def _empty_classification(self) -> Dict[str, str]:
        """Return empty classification for failed attempts"""
        if not self.current_material:
            return {}
        
        categories = self.materials_config[self.current_material].get('classification_categories', [])
        return {self._category_to_key(cat): 'N/A' for cat in categories}
    
    def get_material_info(self, material_name: str) -> Dict:
        """Get configuration info for a specific material"""
        if material_name in self.materials_config:
            return self.materials_config[material_name]
        return {}
    

    def enhance_prompt(self, draft_prompt: str, categories: List[str] = None, 
                       material_name: str = None, material_description: str = None) -> str:
        """
        Enhance a draft prompt using AI to make it more effective.
        
        Args:
            draft_prompt: Basic user-written prompt
            categories: List of classification categories (output columns)
            material_name: Name of the material (e.g., "Menthol", "Steel")
            material_description: Description of the material
        """
        if not draft_prompt:
            return ""
        
        # Enhancer instruction
        enhancer_instruction = """You are a Lead Prompt Architect for Enterprise Data Extraction systems.

Your Goal: EXPAND and REFINE rough drafts into highly detailed, robust system prompts for Gemini.
CRITICAL: Do NOT summarize. Do NOT shorten. You must ELABORATE on the requirements.

Create prompts that:
1. Adopt the PERSONA of an expert Trade Analyst specializing in the SPECIFIC material type
2. Use the placeholder `{description}` for input
3. Define EACH output field with:
   - Clear definition of what to extract
   - Expected values or formats (e.g., "BP Grade", "USP", "Technical")
   - Fallback behavior (e.g., "If not found, return 'Unknown'")
   - Relevant keywords to look for
4. Include material-specific domain knowledge (e.g., for Menthol: common grades are BP, USP, IP, JP; major origins are India, China, Indonesia)
5. Handle edge cases:
   - Mixed products or blends
   - Abbreviated terms
   - Missing information
6. Enforce strict JSON output with the exact category names as keys

Return ONLY the text of the generated prompt, ready to use as a system instruction."""
        
        # Build context-rich meta prompt
        context_parts = []
        
        if material_name:
            context_parts.append(f"Material Type: {material_name}")
        
        if material_description:
            context_parts.append(f"Material Description: {material_description}")
        
        if categories:
            context_parts.append(f"Required Output Columns (JSON keys): {', '.join(categories)}")
            context_parts.append(f"Number of columns to extract: {len(categories)}")
        
        context_str = "\n".join(context_parts) if context_parts else "General trade data extraction"
        
        meta_prompt = f"""User's Draft Prompt: "{draft_prompt}"

Context:
{context_str}

Generate a comprehensive system prompt that:
1. Is specifically tailored for {material_name or 'this material'} extraction
2. Defines extraction rules for EACH of these categories: {', '.join(categories) if categories else 'infer from draft'}
3. Includes domain knowledge relevant to {material_name or 'trade data'}
4. Outputs JSON with keys matching exactly: {categories if categories else 'the fields mentioned'}"""

        try:
            # Call Claude for prompt enhancement
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": enhancer_instruction},
                    {"role": "user", "content": meta_prompt}
                ],
                temperature=0.8,
                max_tokens=2048
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            raise e


if __name__ == "__main__":
    # Test the agent
    try:
        agent = TradeDataAgent()
        print(f"Available materials: {agent.get_available_materials()}")
        
        # Test with Betaines
        agent.set_material("Betaines")
        test_description = "CAPB-35 Cosmetic Grade from Germany, 35% active matter, pH 5.0-6.5"
        result = agent.classify_description(test_description)
        print(f"\nTest classification result:\n{json.dumps(result, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")
