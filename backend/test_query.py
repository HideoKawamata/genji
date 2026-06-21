import os
from dotenv import load_dotenv
load_dotenv()

import chromadb
import vertexai
from vertexai.generative_models import GenerativeModel
from data_loader import GCPVertexEmbeddingFunction

print("Initializing ChromaDB...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = GCPVertexEmbeddingFunction()

try:
    collection = chroma_client.get_collection(name="genji_collection", embedding_function=embedding_function)
    print(f"Collection count: {collection.count()}")
    
    concern = "最近、職場の同期が先に昇進して焦っている。"
    print(f"Querying for concern: '{concern}'")
    
    results = collection.query(
        query_texts=[concern],
        n_results=2
    )
    
    print("\nQuery results:")
    for doc in results['documents'][0]:
        print("-" * 40)
        print(doc)
    
    # Try gemini call
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GCP_REGION", "asia-northeast1")
    vertexai.init(project=project, location=location)
    
    print("\nInitializing gemini-2.5-flash...")
    model = GenerativeModel("gemini-2.5-flash")
    
    context_text = "\n\n".join(results['documents'][0])
    prompt = f"悩みに共感してください。悩み: {concern}\n\n関連エピソード:\n{context_text}"
    
    print("Generating response...")
    response = model.generate_content(prompt)
    print("\nGemini Response:")
    print(response.text)
    
except Exception as e:
    print(f"Failed: {e}")
