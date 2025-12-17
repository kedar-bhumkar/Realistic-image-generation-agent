import os
from openai import OpenAI
import json

class OpenAIGenerator:
    def __init__(self):
        print("Initializing OpenAI Generator...")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY must be set in environment variables.")
            raise ValueError("OPENAI_API_KEY must be set in environment variables.")
        self.client = OpenAI(api_key=api_key)
        print("OpenAI Generator initialized.")

    def generate_image_prompts(self, prompt_instruction: str, count: int, model: str = "gpt-4o"):
        """
        Generates 'count' highly detailed image prompts based on the instruction.
        """
        print(f"Generating {count} image prompts using model '{model}'...")
        system_message = (
            "You are a creative assistant that generates highly detailed image generation prompts. "
            "Output your response as a JSON object with a key 'prompts' which is a list of strings."
        )
        
        user_message = (
            f"Based on the following instructions, generate {count} unique, highly detailed image prompts:\n\n"
            f"Instructions: {prompt_instruction}"
        )

        try:
            print("Sending request to OpenAI...")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            prompts = data.get("prompts", [])
            print(f"Successfully received {len(prompts)} prompts from OpenAI.")
            return prompts
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return []

