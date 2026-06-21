import os
from dotenv import load_dotenv
load_dotenv()

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

project = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GCP_REGION", "us-central1") # Try us-central1 as it is more likely to support Imagen
vertexai.init(project=project, location=location)

print(f"Project: {project}, Region: {location}")

imagen_models = [
    "imagen-3.0-generate-002",
    "imagen-3.0-generate-001",
]

for model_name in imagen_models:
    try:
        print(f"Trying Imagen Model: {model_name}...")
        image_model = ImageGenerationModel.from_pretrained(model_name)
        images = image_model.generate_images(
            prompt="A beautiful Japanese Heian period scroll painting under the moonlight.",
            number_of_images=1,
            aspect_ratio="16:9"
        )
        print("Success! Generated image object type:", type(images[0]))
        # Save image locally
        images[0].save("test_imagen_output.png")
        print("Image saved successfully to test_imagen_output.png")
        break
    except Exception as e:
        print(f"Failed with {model_name}: {e}")
