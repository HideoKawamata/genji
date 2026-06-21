import os
from dotenv import load_dotenv
load_dotenv()

import chromadb
from data_loader import GCPVertexEmbeddingFunction

chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = GCPVertexEmbeddingFunction()

try:
    collection = chroma_client.get_collection(name="genji_collection", embedding_function=embedding_function)
    print(f"Collection exists. Item count: {collection.count()}")
except Exception as e:
    print(f"Collection does not exist or failed to load: {e}")
