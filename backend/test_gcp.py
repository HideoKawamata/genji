import os
from dotenv import load_dotenv
load_dotenv()

import vertexai
from vertexai.generative_models import GenerativeModel

project = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GCP_REGION", "asia-northeast1")

print(f"Project: {project}, Location: {location}")

models_to_try = [
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro-002"
]

regions_to_try = [
    "asia-northeast1",
    "us-central1"
]

for region in regions_to_try:
    print(f"\n--- Testing with Region: {region} ---")
    try:
        vertexai.init(project=project, location=region)
        print(f"Vertex AI initialized for region {region}")
    except Exception as e:
        print(f"Initialization failed for region {region}: {e}")
        continue
        
    for model_name in models_to_try:
        try:
            print(f"Trying model: {model_name} in {region}...")
            model = GenerativeModel(model_name)
            response = model.generate_content("Hello")
            print(f"  SUCCESS! Response: {response.text.strip()}")
        except Exception as e:
            print(f"  FAILED: {e}")
