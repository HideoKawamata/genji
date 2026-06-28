import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import chromadb
from vertexai.language_models import TextEmbeddingModel

# Load environment variables
load_dotenv()

URLS = [
    {"title": "桐壺", "url": "https://www.aozora.gr.jp/cards/000052/files/5016_9758.html"},
    {"title": "帚木", "url": "https://www.aozora.gr.jp/cards/000052/files/5017_9759.html"},
    {"title": "空蝉", "url": "https://www.aozora.gr.jp/cards/000052/files/5018_9760.html"},
    {"title": "夕顔", "url": "https://www.aozora.gr.jp/cards/000052/files/5019_9762.html"},
    {"title": "若紫", "url": "https://www.aozora.gr.jp/cards/000052/files/5020_11254.html"},
    {"title": "末摘花", "url": "https://www.aozora.gr.jp/cards/000052/files/5021_11107.html"},
    {"title": "紅葉賀", "url": "https://www.aozora.gr.jp/cards/000052/files/5022_11633.html"},
    {"title": "花宴", "url": "https://www.aozora.gr.jp/cards/000052/files/5023_10175.html"},
    {"title": "葵", "url": "https://www.aozora.gr.jp/cards/000052/files/5024_11085.html"},
    {"title": "賢木", "url": "https://www.aozora.gr.jp/cards/000052/files/5025_11636.html"},
    {"title": "花散里", "url": "https://www.aozora.gr.jp/cards/000052/files/5026_11638.html"},
    {"title": "須磨", "url": "https://www.aozora.gr.jp/cards/000052/files/5027_11270.html"},
    {"title": "明石", "url": "https://www.aozora.gr.jp/cards/000052/files/5028_11650.html"},
    {"title": "澪標", "url": "https://www.aozora.gr.jp/cards/000052/files/5029_10177.html"},
    {"title": "蓬生", "url": "https://www.aozora.gr.jp/cards/000052/files/5030_10219.html"},
    {"title": "関屋", "url": "https://www.aozora.gr.jp/cards/000052/files/5031_10221.html"},
    {"title": "絵合", "url": "https://www.aozora.gr.jp/cards/000052/files/5032_10223.html"},
    {"title": "松風", "url": "https://www.aozora.gr.jp/cards/000052/files/5033_11020.html"},
    {"title": "薄雲", "url": "https://www.aozora.gr.jp/cards/000052/files/5034_11648.html"},
    {"title": "朝顔", "url": "https://www.aozora.gr.jp/cards/000052/files/5035_11652.html"},
    {"title": "少女", "url": "https://www.aozora.gr.jp/cards/000052/files/5036_11906.html"},
    {"title": "玉鬘", "url": "https://www.aozora.gr.jp/cards/000052/files/5037_11910.html"},
    {"title": "初音", "url": "https://www.aozora.gr.jp/cards/000052/files/5038_10199.html"},
    {"title": "胡蝶", "url": "https://www.aozora.gr.jp/cards/000052/files/5039_11657.html"},
    {"title": "蛍", "url": "https://www.aozora.gr.jp/cards/000052/files/5040_11669.html"},
    {"title": "常夏", "url": "https://www.aozora.gr.jp/cards/000052/files/5041_12171.html"},
    {"title": "篝火", "url": "https://www.aozora.gr.jp/cards/000052/files/5042_11844.html"},
    {"title": "野分", "url": "https://www.aozora.gr.jp/cards/000052/files/5043_10262.html"},
    {"title": "行幸", "url": "https://www.aozora.gr.jp/cards/000052/files/5044_10287.html"},
    {"title": "藤袴", "url": "https://www.aozora.gr.jp/cards/000052/files/5045_11024.html"},
    {"title": "真木柱", "url": "https://www.aozora.gr.jp/cards/000052/files/5046_12198.html"},
    {"title": "梅枝", "url": "https://www.aozora.gr.jp/cards/000052/files/5047_12202.html"},
    {"title": "藤裏葉", "url": "https://www.aozora.gr.jp/cards/000052/files/5048_12252.html"},
    {"title": "若菜上", "url": "https://www.aozora.gr.jp/cards/000052/files/5049_14830.html"},
    {"title": "若菜下", "url": "https://www.aozora.gr.jp/cards/000052/files/5050_14552.html"},
    {"title": "柏木", "url": "https://www.aozora.gr.jp/cards/000052/files/5051_14567.html"},
    {"title": "横笛", "url": "https://www.aozora.gr.jp/cards/000052/files/5052_13280.html"},
    {"title": "鈴虫", "url": "https://www.aozora.gr.jp/cards/000052/files/5053_12173.html"},
    {"title": "夕霧", "url": "https://www.aozora.gr.jp/cards/000052/files/5054_10249.html"},
    {"title": "御法", "url": "https://www.aozora.gr.jp/cards/000052/files/5055_10251.html"},
    {"title": "幻", "url": "https://www.aozora.gr.jp/cards/000052/files/5056_13291.html"},
    {"title": "匂宮", "url": "https://www.aozora.gr.jp/cards/000052/files/5057_14554.html"},
    {"title": "紅梅", "url": "https://www.aozora.gr.jp/cards/000052/files/5058_14558.html"},
    {"title": "竹河", "url": "https://www.aozora.gr.jp/cards/000052/files/5059_11969.html"},
    {"title": "橋姫", "url": "https://www.aozora.gr.jp/cards/000052/files/5060_15278.html"},
    {"title": "椎本", "url": "https://www.aozora.gr.jp/cards/000052/files/5061_15280.html"},
    {"title": "総角", "url": "https://www.aozora.gr.jp/cards/000052/files/5062_15326.html"},
    {"title": "早蕨", "url": "https://www.aozora.gr.jp/cards/000052/files/5063_15328.html"},
    {"title": "宿木", "url": "https://www.aozora.gr.jp/cards/000052/files/5064_15564.html"},
    {"title": "東屋", "url": "https://www.aozora.gr.jp/cards/000052/files/5065_15348.html"},
    {"title": "浮舟", "url": "https://www.aozora.gr.jp/cards/000052/files/5066_16261.html"},
    {"title": "蜻蛉", "url": "https://www.aozora.gr.jp/cards/000052/files/5067_16265.html"},
    {"title": "手習", "url": "https://www.aozora.gr.jp/cards/000052/files/5068_17944.html"},
    {"title": "夢浮橋", "url": "https://www.aozora.gr.jp/cards/000052/files/5069_16428.html"}
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

def chunk_text(text: str, max_chars: int = 300) -> list[str]:
    """
    Semantic chunking: splits text at sentence boundaries (。！？)
    instead of fixed character counts.
    
    Args:
        text: 分割対象の日本語テキスト
        max_chars: 1チャンクあたりの最大文字数（目安）
    Returns:
        チャンクのリスト
    """
    import re
    # ステップ1: 文単位分割
    sentences = re.split(r'(?<=[。！？．])\n?', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # ステップ2: 文をグルーピングしてチャンク生成
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_len = len(sentence)
        if current_length + sentence_len > max_chars and current_length > 0:
            chunks.append("".join(current_chunk))
            # ステップ3: オーバーラップの追加 (1文オーバーラップ)
            current_chunk = [current_chunk[-1], sentence]
            current_length = len(current_chunk[0]) + sentence_len
        else:
            current_chunk.append(sentence)
            current_length += sentence_len
            
    if current_chunk:
        chunks.append("".join(current_chunk))
        
    # ステップ4: 最小チャンク長フィルタ
    final_chunks = [c for c in chunks if len(c) >= 30]
    return final_chunks

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
        print(f"{title}: {len(chunks)} chunks created (semantic, avg {sum(len(c) for c in chunks)//max(len(chunks),1)} chars/chunk)")
        
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
