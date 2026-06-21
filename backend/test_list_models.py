import os
from dotenv import load_dotenv
load_dotenv()

import vertexai
from google.cloud import aiplatform

project = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GCP_REGION", "asia-northeast1")
vertexai.init(project=project, location=location)

print("Initializing AI Platform Client...")
aiplatform.init(project=project, location=location)

try:
    print("Listing Models...")
    # List model registry models
    models = aiplatform.Model.list()
    print(f"Models in registry ({len(models)}):")
    for m in models:
        print(f" - {m.display_name} ({m.resource_name})")
except Exception as e:
    print(f"Listing models failed: {e}")
