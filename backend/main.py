from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import chromadb
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Vertex AI related libraries for GCP
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel

# Use the same EmbeddingFunction class defined in data_loader
from data_loader import GCPVertexEmbeddingFunction

load_dotenv()

app = FastAPI(title="Genji-Mirror API")

# Register authentication router
from auth import router as auth_router
app.include_router(auth_router)

# CORS configuration (allow access from Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development. Restrict to frontend URL in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving configuration (save destination for generated images)
import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = GCPVertexEmbeddingFunction()

try:
    collection = chroma_client.get_collection(name="genji_collection", embedding_function=embedding_function)
except Exception as e:
    print(f"Warning: Could not load collection. Please run data_loader.py first. {e}")
    collection = None

class ConsultRequest(BaseModel):
    concern: str

class ConsultResponse(BaseModel):
    character: str
    message: str
    explanation: str
    waka: str
    waka_translation: str
    image_url: str

@app.post("/api/consult", response_model=ConsultResponse)
async def consult(request: ConsultRequest):
    if not collection:
        raise HTTPException(status_code=500, detail="ChromaDB collection is not initialized.")

    concern = request.concern

    # 1. Search for similar scenes
    try:
        results = collection.query(
            query_texts=[concern],
            n_results=3
        )
        context_chunks = results['documents'][0]
        context_text = "\n\n".join(context_chunks)
    except Exception as e:
        print(f"Search failed: {e}")
        context_text = "(No context due to search error)"

    # 2. Generate empathetic text and Waka using Gemini 2.5 Flash
    try:
        import os
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GCP_REGION", "asia-northeast1")
        if project:
            vertexai.init(project=project, location=location)
            
        model = GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
You are "Genji-Mirror", a mirror that deeply empathizes with the characters of "The Tale of Genji" from 1000 years ago, and delivers their words to modern people.
Based on the following [Concern] from a modern person and the [Related Episode] from The Tale of Genji, deeply empathize and encourage them from the perspective of a specific character.

[Concern]
{concern}

[Related Episode (Search Result)]
{context_text}

Please output in the following format (JSON). Do not add Markdown code blocks (```json ... ```), output the JSON string directly. Ensure that all text values in the JSON (character, message, explanation, waka, waka_translation) are written entirely in Japanese, except for image_prompt which must be in English.
{{
  "character": "Name of the empathetic character (e.g., Hikaru Genji, Lady Rokujo, Murasaki Shikibu, etc.)",
  "message": "A deep empathetic and healing message from that character",
  "explanation": "A brief explanation of the relevant scene in The Tale of Genji, explaining why the character can empathize",
  "waka": "A waka poem that fits this situation (can be a real one, or one created by Gemini)",
  "waka_translation": "A modern translation of that waka poem",
  "image_prompt": "An English prompt to generate a scroll-style image representing this situation. A beautiful composition fusing modern concerns with the Heian world."
}}
"""
        response = model.generate_content(prompt)
        # Simple JSON parsing
        import json
        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()
            
        generated_data = json.loads(text_response)
        
    except Exception as e:
        print(f"Gemini generation failed: {e}")
        # Fallback dummy data
        generated_data = {
            "character": "Hikaru Genji",
            "message": "Because GCP API (Vertex AI) settings are invalid or unauthorized, a temporary message is displayed. I understand your concerns well.",
            "explanation": "Failed to search The Tale of Genji and generate text due to a configuration error. Please enable the API in your GCP project.",
            "waka": "秋の夜の 月の光は 清けれど 悩める心 照らしきれずや",
            "waka_translation": "The moonlight on an autumn night is pure, but it seems unable to illuminate your troubled heart.",
            "image_prompt": "A beautiful Japanese Heian period scroll painting showing a modern person consulting with Prince Genji under the moonlight."
        }

    # 3. Image generation by Imagen 3
    image_url = ""
    try:
        from vertexai.preview.vision_models import ImageGenerationModel
        import uuid
        
        # Use model name "imagen-3.0-generate-002"
        image_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        
        images = image_model.generate_images(
            prompt=generated_data.get("image_prompt", "A beautiful Japanese Heian period scroll painting."),
            number_of_images=1,
            aspect_ratio="16:9"
        )
        
        # Save the generated image to the static folder
        filename = f"gen_{uuid.uuid4().hex}.png"
        filepath = os.path.join("static", filename)
        images[0].save(filepath, include_generation_parameters=False)
        
        # Build absolute URL directly accessible by frontend
        image_url = f"http://127.0.0.1:8000/static/{filename}"
        print(f"Successfully generated and saved Imagen image: {filepath}")
        
    except Exception as e:
        print(f"Imagen generation failed, attempting fallback: {e}")
        # Placeholder image
        image_url = "https://images.unsplash.com/photo-1545161252-78d10ed73775?q=80&w=1000&auto=format&fit=crop"

    return ConsultResponse(
        character=generated_data.get("character", "Unknown"),
        message=generated_data.get("message", "An error occurred."),
        explanation=generated_data.get("explanation", ""),
        waka=generated_data.get("waka", ""),
        waka_translation=generated_data.get("waka_translation", ""),
        image_url=image_url
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
