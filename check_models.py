import asyncio
import os
from google import genai

async def check_models():
    api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("ERROR: GOOGLE_API_KEY environment variable not found!")
        return

    try:
        client = genai.Client(api_key=api_key)
        print("Fetching all available models for your API Key...\n")
        
        # Get the list of models
        model_list = await client.aio.models.list()
        
        # Just print the names directly to avoid attribute errors
        for model in model_list:
            print(f"-> {model.name}")
                
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(check_models())