import os
from supabase import create_client, Client

class SupabaseManager:
    def __init__(self):
        print("Initializing Supabase Manager...")
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            print("Error: SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
        self.supabase: Client = create_client(url, key)
        print("Supabase Manager initialized successfully.")

    def get_prompt_config(self, category_type: str):
        """
        Fetches prompt_instruction and image_urls from nano_banana_prompt_config
        where type matches the given category_type.
        """
        print(f"Fetching prompt config for category: '{category_type}'...")
        try:
            response = self.supabase.table("nano_banana_prompt_config") \
                .select("system_prompt, standard_prompt, dynamic_prompt, image_urls") \
                .eq("category_type", category_type) \
                .execute()
            
            # response.data is a list of dictionaries
            if response.data and len(response.data) > 0:
                # Assuming we just want the first match or random one. 
                # The prompt implies a single config per type or at least one is sufficient.
                # Let's pick the first one.
                print(f"Successfully retrieved config for '{category_type}'.")
                return response.data[0]
            else:
                print(f"No configuration found for category: '{category_type}'")
                return None
        except Exception as e:
            print(f"Error fetching from Supabase: {e}")
            return None

    def append_generated_prompts(self, category_type: str, new_prompts: list):
        """
        Appends new_prompts to the existing generated_prompt array in nano_banana_prompt_config
        for the given category_type.
        """
        print(f"Appending {len(new_prompts)} prompts to category: '{category_type}'...")
        try:
            # 1. Fetch existing prompts
            response = self.supabase.table("nano_banana_prompt_config") \
                .select("generated_prompts") \
                .eq("category_type", category_type) \
                .execute()
            
            existing_prompts = []
            if response.data and len(response.data) > 0:
                 existing_prompts = response.data[0].get("generated_prompts")
                 if existing_prompts is None:
                     existing_prompts = []
            
            # 2. Append new prompts
            updated_prompts = existing_prompts + new_prompts
            
            # 3. Update the table
            self.supabase.table("nano_banana_prompt_config") \
                .update({"generated_prompts": updated_prompts}) \
                .eq("category_type", category_type) \
                .execute()
            print("Successfully updated generated_prompts.")
        except Exception as e:
            print(f"Error updating Supabase: {e}")

    def get_model_config(self, model_version: str = None):
        """
        Fetches the model configuration from model_config table.
        If model_version is provided, filters by name=model_version.
        Otherwise, filters by isActive=true and type='image'.
        """
        print(f"Fetching model config from Supabase... (model_version={model_version})")
        try:
            query = self.supabase.table("model_config").select("name, config")
            
            if model_version:
                # 1. Accept a new optional parameter 'model_version'
                # 2. If present, use the model_version as a filter. Drop all other existing fields.
                query = query.eq("name", model_version)
            else:
                # 3. If not present use the present code to get the model_config based on existing filters
                query = query.eq("isActive", True).eq("type", "image")
            
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                # Assuming we want the first match
                row = response.data[0]
                config = row.get("config", {})
                name = row.get("name")
                
                # Inject name as model_version if present
                if name:
                    config["model_version"] = name
                    
                print(f"Successfully retrieved model config. Name: {name}, Config: {config}")
                return config
            else:
                print("No matching model configuration found.")
                return None
        except Exception as e:
            print(f"Error fetching model config: {e}")
            return None

# chotemiyan!