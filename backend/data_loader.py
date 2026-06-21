import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import chromadb
from vertexai.language_models import TextEmbeddingModel

# Load environment variables
load_dotenv()

# URL list of modern translations of The Tale of Genji (Yosano Akiko translation, Aozora Bunko)
URLS = [
    {"title": "桐壺", "url": "https://www.aozora.gr.jp/cards/000052/files/5016_9758.html"},
    {"title": "帚木", "url": "https://www.aozora.gr.jp/cards/000052/files/5017_9759.html"},
    {"title": "空蝉", "url": "https://www.aozora.gr.jp/cards/000052/files/5018_9760.html"},
    {"title": "夕顔", "url": "https://www.aozora.gr.jp/cards/000052/files/5019_9761.html"},
]

def fetch_aozora_text(url):
    """Extract the main text from Aozora Bunko HTML"""
    print(f"Downloading: {url}")
    response = requests.get(url)
    response.encoding = 'shift_jis'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove ruby text (remove <rt> tags, etc.)
    for rt in soup.find_all('rt'):
        rt.decompose()
    for rp in soup.find_all('rp'):
        rp.decompose()
        
    main_text_div = soup.find('div', class_='main_text')
    if not main_text_div:
        return ""
    
    text = main_text_div.get_text()
    
    # Clean up line breaks and whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\u3000', ' ', text)
    return text

def chunk_text(text, chunk_size=300, overlap=50):
    """Chunk text by a certain number of characters"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

class GCPVertexEmbeddingFunction(chromadb.EmbeddingFunction):
    """Vertex AI Embedding function for ChromaDB"""
    
    def name(self) -> str:
        return "GCPVertexEmbeddingFunction"
    
    def __init__(self, model_name="text-multilingual-embedding-002"):
        import vertexai
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GCP_REGION", "asia-northeast1")
        if project:
            vertexai.init(project=project, location=location)
        try:
            self.model = TextEmbeddingModel.from_pretrained(model_name)
        except Exception as e:
            print(f"Vertex AI Embedding Model initialization failed: {e}")
            self.model = None

    def __call__(self, input):
        # input is a list of strings
        if not self.model:
            print("Warning: GCP embedding model not available, using fallback (empty vectors)")
            return [[0.0]*768 for _ in input]
            
        try:
            embeddings = self.model.get_embeddings(input)
            return [embedding.values for embedding in embeddings]
        except Exception as e:
            print(f"Failed to get embeddings: {e}")
            return [[0.0]*768 for _ in input]

def main():
    print("Starting data preparation...")
    
    # Initialize ChromaDB (save to local directory)
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    # Prepare Vertex AI Embedding function
    embedding_function = GCPVertexEmbeddingFunction()
    
    # Get or create collection
    collection_name = "genji_collection"
    try:
        collection = chroma_client.get_collection(name=collection_name, embedding_function=embedding_function)
        print(f"Using existing collection '{collection_name}'.")
    except Exception:
        collection = chroma_client.create_collection(name=collection_name, embedding_function=embedding_function)
        print(f"Created new collection '{collection_name}'.")

    # Simple check to skip if data already exists
    if collection.count() > 0:
        print(f"The collection already has {collection.count()} chunks saved.")
        choice = input("Do you want to reload the data? (y/n): ")
        if choice.lower() != 'y':
            print("Skipping data preparation.")
            return

    all_ids = []
    all_documents = []
    all_metadatas = []

    chunk_id_counter = 0

    for item in URLS:
        title = item["title"]
        url = item["url"]
        
        text = fetch_aozora_text(url)
        if not text:
            print(f"Warning: Failed to fetch text for {title}.")
            continue
            
        chunks = chunk_text(text)
        print(f"{title}: Created {len(chunks)} chunks.")
        
        for i, chunk in enumerate(chunks):
            chunk_id_counter += 1
            doc_id = f"{title}_chunk_{i}"
            
            all_ids.append(doc_id)
            all_documents.append(chunk)
            all_metadatas.append({"title": title, "chunk_index": i})

    if all_documents:
        print(f"Inserting a total of {len(all_documents)} chunks into ChromaDB. Please wait...")
        
        # Process in batches considering API limits
        batch_size = 100
        for i in range(0, len(all_documents), batch_size):
            end_idx = min(i + batch_size, len(all_documents))
            batch_ids = all_ids[i:end_idx]
            batch_documents = all_documents[i:end_idx]
            batch_metadatas = all_metadatas[i:end_idx]
            
            print(f"Inserting batch... {i} - {end_idx} / {len(all_documents)}")
            collection.upsert(
                ids=batch_ids,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
        
        print("Vector DB construction completed!")
    else:
        print("No data to insert.")

if __name__ == "__main__":
    main()
