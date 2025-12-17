import os
import sys
import importlib.util
from dotenv import load_dotenv
from src.orchestrator import Orchestrator

# Load environment variables
load_dotenv()

# Import legacy module for image generation
# We do this because the file has hyphens in the name
try:
    spec = importlib.util.spec_from_file_location("nano_banana_pro", "nano-banana-pro.py")
    nano_banana_pro = importlib.util.module_from_spec(spec)
    sys.modules["nano_banana_pro"] = nano_banana_pro
    spec.loader.exec_module(nano_banana_pro)
    NanoBananaProGenerator = nano_banana_pro.NanoBananaProGenerator
except Exception as e:
    print(f"Warning: Could not import NanoBananaProGenerator from nano-banana-pro.py: {e}")
    NanoBananaProGenerator = None

def main(save_remotely=True, drive_folder_id="1H4wWGNaY01skMzUvQtQmHWlabaTc4rHx", category=None, min_val=None, max_val=None, resolution=None, aspect_ratio=None, mode="standard", model_version=None, image_urls=None, prompts=None):
    print("Starting Nano Banana Pro Orchestrator...")
    
    # Initialize Orchestrator
    try:
        orchestrator = Orchestrator()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please ensure you have set up your .env file correctly.")
        return

    # Fetch default config if parameters are missing
    # Default fallback if nothing found in DB
    default_model_version = "google/nano-banana-pro" 
    db_config = {}

    print("Fetching default model configuration...")
    # Pass model_version to get_model_config to filter by it if provided
    fetched_config = orchestrator.get_model_config(model_version=model_version)
    if fetched_config:
        db_config = fetched_config
        # Extract model_version if present in DB config (which it should be if we filtered by it)
        if "model_version" in db_config:
            model_version = db_config["model_version"]
            print(f"Using model_version from DB: {model_version}")
    else:
        print("Could not fetch default config. Using hardcoded defaults.")
        if model_version is None:
             model_version = default_model_version

    # Override with command line arguments if provided
    if resolution:
        db_config["resolution"] = resolution
    if aspect_ratio:
        db_config["aspect_ratio"] = aspect_ratio
    
    # Ensure defaults if still missing
    current_res = db_config.get("resolution", "2K")
    current_ar = db_config.get("aspect_ratio", "16:9")
    
    print(f"Final Configuration - Resolution: {current_res}, Aspect Ratio: {current_ar}, Model: {model_version}")

    # Run the flow (Steps 1-4)
    result = orchestrator.run_flow(
        category=category, 
        min_val=min_val, 
        max_val=max_val, 
        mode=mode,
        provided_image_urls=image_urls,
        provided_prompts=prompts
    )
    
    if not result:
        print("Flow failed to produce results.")
        return

    prompts = result["prompts"]
    image_urls = result["image_urls"]
    category = result["category"]

    if not prompts:
        print("No prompts were generated.")
        return

    print("\n--- Summary ---")
    print(f"Category: {category}")
    print(f"Generated {len(prompts)} prompts")
    print(f"Using {len(image_urls)} input images")
    
    # Execute Image Generation (Optional Step)
    if NanoBananaProGenerator and (prompts or image_urls):
        print("\nStarting Image Generation...")
        output_folder = "output/nano_banana_results"
        
        # You might want to pull these from env or config too
        # save_remotely and drive_folder_id are now passed as arguments
        
        generator = NanoBananaProGenerator(output_folder)
        
        # Call generate
        # Note: The original script's generate method takes (prompts, images, ...)
        generator.generate(
            prompts, 
            image_urls, 
            model_version=model_version,
            saveRemotely=save_remotely, 
            drive_folder_id=drive_folder_id,
            input_config=db_config
        )
    else:
        print("\nSkipping image generation (Module not loaded or no data).")
        print("Generated Prompts:")
        for i, p in enumerate(prompts, 1):
            print(f"{i}. {p}")
            
    print("\nNano Banana Pro Orchestrator finished.")

if __name__ == "__main__":
    main()

