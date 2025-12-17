from src.utils import RandomGenerator
from src.database import SupabaseManager
from src.llm import OpenAIGenerator
import random

class Orchestrator:
    def __init__(self):
        self.db_manager = SupabaseManager()
        self.openai_generator = OpenAIGenerator()

    def get_model_config(self, model_version: str = None):
        return self.db_manager.get_model_config(model_version=model_version)

    def run_flow(self, category=None, min_val=None, max_val=None, mode="standard", provided_image_urls=None, provided_prompts=None):
        print("Starting orchestration flow...")

        # Initialize working variables with provided values
        image_urls = provided_image_urls
        prompts = provided_prompts

        # Determine if we need to fetch configuration (if either input is missing)
        needs_config = (image_urls is None) or (prompts is None)
        config = None

        # 1. Select category
        if category:
            print(f"Step 1: Using provided category: {category}")
        elif needs_config:
            print("Step 1: Selecting random category...")
            category = RandomGenerator.get_random_category()
            print(f"Selected Category: {category}")
        else:
            print("Step 1: Skipping category selection (all inputs provided)")

        # 2. Get config from Supabase (only if needed)
        if needs_config and category:
            print("Step 2: Retrieving configuration from Supabase...")
            config = self.db_manager.get_prompt_config(category)
            if not config:
                print(f"No configuration found for category: {category}")
                # We continue, but subsequent steps might fail if they rely on config
        else:
            print("Step 2: Skipping Supabase config retrieval")

        # Determine image_urls if not provided
        if image_urls is None:
            if config:
                image_urls = config.get("image_urls")
                
                # Handle image_urls format (could be list or string)
                if isinstance(image_urls, str):
                    image_urls = [url.strip() for url in image_urls.split(',')]
                elif not isinstance(image_urls, list):
                    image_urls = []
                print(f"Retrieved {len(image_urls)} Image URLs from Supabase")
            else:
                image_urls = []
                print("Warning: No config available. Defaulting to empty image_urls.")
        else:
            print(f"Using provided {len(image_urls)} Image URLs")

        # Determine prompts if not provided
        if prompts is None:
            if config:
                system_prompt = config.get("system_prompt", "")
                selected_instruction = ""

                if mode == "random":
                    print("Mode is 'random'. Using dynamic_prompt.")
                    dynamic_prompts = config.get("dynamic_prompt")
                    if isinstance(dynamic_prompts, list) and dynamic_prompts:
                        selected_instruction = random.choice(dynamic_prompts)
                        print("Selected a dynamic prompt.")
                    else:
                        print("Warning: dynamic_prompt is empty or not a list. Falling back to empty instruction.")
                else:
                    # Default to standard
                    print("Mode is 'standard'. Using standard_prompt.")
                    standard_prompts = config.get("standard_prompt")
                    if isinstance(standard_prompts, list) and standard_prompts:
                        selected_instruction = random.choice(standard_prompts)
                        print("Selected a standard prompt.")
                    else:
                        print("Warning: standard_prompt is empty or not a list. Falling back to empty instruction.")

                # Combine system prompt and selected instruction
                prompt_instruction = f"{system_prompt}\n\n{selected_instruction}"
                
                print(f"Retrieved Instructions: {prompt_instruction[:50]}...") # Truncate for display

                # 3. Generate random prompt count
                print("Step 3: Determining prompt count...")
                
                # Use provided min/max or default to 2 and 5 as per requirements
                target_min = min_val if min_val is not None else 2
                target_max = max_val if max_val is not None else 5
                
                print(f"Using min_val={target_min}, max_val={target_max} for prompt count generation.")
                prompt_count = RandomGenerator.get_random_prompt_count(target_min, target_max)
                print(f"Target Prompt Count: {prompt_count}")

                # 4. Call OpenAI to generate prompts
                print("Step 4: Generating prompts via OpenAI...")
                generated_prompts = self.openai_generator.generate_image_prompts(
                    prompt_instruction, 
                    prompt_count
                )
                
                print(f"Generated {len(generated_prompts)} prompts.")

                # 5. Save generated prompts to Supabase
                if generated_prompts:
                    print("Step 5: Appending generated prompts to Supabase...")
                    self.db_manager.append_generated_prompts(category, generated_prompts)
                
                prompts = generated_prompts
            else:
                prompts = []
                print("Error: No config available to generate prompts.")
        else:
            print(f"Using {len(prompts)} provided prompts.")

        print("Orchestration flow completed successfully.")
        return {
            "category": category,
            "image_urls": image_urls,
            "prompts": prompts
        }

