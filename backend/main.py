from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import chromadb
import asyncio
import json
import os
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from collections import defaultdict
from typing import Optional

# Vertex AI related libraries for GCP
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel
from sentence_transformers import CrossEncoder

# A: Import CHAPTER_LIST for metadata filtering (Gao et al. 2023 §3.2)
from data_loader import GCPVertexEmbeddingFunction, CHAPTER_LIST

load_dotenv()

app = FastAPI(title="Genji-Mirror API")

# Register authentication router
from auth import router as auth_router
app.include_router(auth_router)

# CORS configuration (allow access from Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. Restrict to frontend URL in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving configuration (save destination for generated images)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = GCPVertexEmbeddingFunction()

try:
    collection = chroma_client.get_collection(
        name="genji_collection", embedding_function=embedding_function
    )
except Exception as e:
    print(f"Warning: Could not load collection. Please run data_loader.py first. {e}")
    collection = None

# Initialize Re-ranker (Advanced RAG)
try:
    reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    print("Re-ranker loaded successfully.")
except Exception as e:
    print(f"Warning: Re-ranker could not be loaded: {e}")
    reranker = None

# C: Multi-turn RAG — In-memory session history
# key: session_id, value: list of {concern, character, message}
# Note: For production, replace with Redis or a persistent store.
session_history: dict[str, list[dict]] = defaultdict(list)


# ────────────────────────────────────────────
# Data Models
# ────────────────────────────────────────────

class ConsultRequest(BaseModel):
    concern: str
    session_id: Optional[str] = None  # C: Multi-turn — omit to use "default" session


class ConsultResponse(BaseModel):
    character: str
    message: str
    explanation: str
    waka: str
    waka_translation: str
    image_url: str


# ────────────────────────────────────────────
# Helper: Thread-safe ChromaDB query wrapper
# ────────────────────────────────────────────

def _query_collection(query_text: str, n_results: int, where: Optional[dict] = None) -> dict:
    """
    E: Async-compatible ChromaDB query helper.
    Called via asyncio.to_thread() to avoid blocking the event loop.
    """
    if where:
        return collection.query(
            query_texts=[query_text], n_results=n_results, where=where
        )
    return collection.query(query_texts=[query_text], n_results=n_results)


# ────────────────────────────────────────────
# Helper Functions (RAG Pipeline)
# ────────────────────────────────────────────

def detect_relevant_chapters(concern: str, model: GenerativeModel) -> list[str]:
    """
    A: Metadata Filtering — ユーザーの悩みから関連する源氏物語の巻を最大3つ推定する。
    ChromaDB検索の where 句で使用し、無関係な巻からのノイズを削減する。

    論文: Gao et al. (2023) arXiv:2312.10997 §3.2 「Structured Retrieval」
    効果: 検索空間を意味的に絞ることでRe-rankingの精度が向上する。
    """
    chapters_str = "、".join(CHAPTER_LIST)
    try:
        prompt = (
            f"以下の悩みに最も関連する源氏物語の巻を3つ選んでください。\n"
            f"選択肢（54巻）: {chapters_str}\n\n"
            f"悩み: {concern}\n\n"
            "選んだ巻の名前をカンマ区切りで出力してください。説明不要。\n"
            "例: 須磨,桐壺,葵"
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        chapters = [c.strip() for c in raw.split(",") if c.strip() in CHAPTER_LIST]
        print(f"[A] Relevant chapters detected: {chapters}")
        return chapters
    except Exception as e:
        print(f"[A] Chapter detection failed: {e}")
        return []


def generate_hypothetical_document(concern: str, model: GenerativeModel) -> str:
    """
    HyDE (Hypothetical Document Embeddings, Gao et al. 2022 arXiv:2212.10496):
    現代人の悩みを源氏物語の場面テキストに変換してからベクトル検索を行う。
    クエリ空間とドキュメント空間のギャップを埋め、語彙の不一致問題を解消する。

    E: detect_relevant_chapters() と並列実行される（asyncio.gather）。
    """
    try:
        prompt = (
            "あなたは源氏物語の専門家です。\n"
            "以下の現代人の悩みに最も関連する源氏物語の場面を、\n"
            "与謝野晶子訳の文体で100文字程度で描写してください。\n"
            f"悩み: {concern}\n"
            "場面描写のみを出力し、説明や前置きは不要です。"
        )
        response = model.generate_content(prompt)
        result = response.text.strip()
        print(f"[HyDE] query generated: {result[:50]}...")
        return result
    except Exception as e:
        print(f"[HyDE] generation failed: {e}")
        return concern


def rewrite_query_with_history(
    concern: str, history: list[dict], model: GenerativeModel
) -> str:
    """
    C: Multi-turn RAG — 会話履歴を踏まえてクエリを書き換える。
    「もっと詳しく」「他のキャラは？」などの省略的な表現を
    単独で検索可能な完全なクエリに変換する。

    論文: NVIDIA Query Rewriting for Multi-turn RAG (2024)
    """
    if not history:
        return concern
    try:
        history_text = "\n".join([
            f"Q: {h['concern']}\nA: {h.get('character', '不明')}からの回答: {h.get('message', '')}"
            for h in history[-3:]  # 直近3ターンのみ使用
        ])
        prompt = (
            "以下の会話履歴と新しい質問を踏まえて、\n"
            "新しい質問を単独で意味が通る完全な文章に書き換えてください。\n\n"
            f"会話履歴:\n{history_text}\n\n"
            f"新しい質問: {concern}\n\n"
            "書き換えた質問のみを出力してください。"
        )
        response = model.generate_content(prompt)
        rewritten = response.text.strip()
        print(f"[C] Query rewritten: {rewritten[:60]}...")
        return rewritten
    except Exception as e:
        print(f"[C] Query rewriting failed: {e}")
        return concern


# ────────────────────────────────────────────
# Main API Endpoint
# ────────────────────────────────────────────

@app.post("/api/consult", response_model=ConsultResponse)
async def consult(request: ConsultRequest):
    if not collection:
        raise HTTPException(
            status_code=500, detail="ChromaDB collection is not initialized."
        )

    concern = request.concern
    session_id = request.session_id or "default"
    history = list(session_history[session_id])  # スレッドセーフなコピー

    # Initialize Vertex AI and Gemini model
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GCP_REGION", "asia-northeast1")
    if project:
        vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-flash")

    # ── Phase 1: Query Preparation ──────────────────────────────────────────

    # C: Multi-turn — 会話履歴があればクエリを書き換え
    effective_concern = concern
    if history:
        effective_concern = await asyncio.to_thread(
            rewrite_query_with_history, concern, history, model
        )

    # E: Async Parallel — HyDE生成 と 関連巻検出 を並列実行
    # 両者ともGemini呼び出しだが互いに独立しているため同時実行可能
    # 直列時: ~3秒 → 並列時: ~1.5秒（約50%削減）
    hyde_task = asyncio.to_thread(
        generate_hypothetical_document, effective_concern, model
    )
    chapters_task = asyncio.to_thread(
        detect_relevant_chapters, effective_concern, model
    )

    hyde_query, relevant_chapters = await asyncio.gather(
        hyde_task, chapters_task, return_exceptions=True
    )

    # 例外フォールバック処理
    if isinstance(hyde_query, Exception):
        print(f"[HyDE] Task failed with exception: {hyde_query}")
        hyde_query = effective_concern
    if isinstance(relevant_chapters, Exception):
        print(f"[A] Chapter task failed with exception: {relevant_chapters}")
        relevant_chapters = []

    # ── Phase 2: Retrieval ──────────────────────────────────────────────────

    context_chunks: list[str] = []
    context_metadatas: list[dict] = []

    try:
        # A: Metadata Filtering — 関連巻のみに絞って検索
        where_clause = (
            {"title": {"$in": relevant_chapters}} if relevant_chapters else None
        )
        results = await asyncio.to_thread(
            _query_collection, str(hyde_query), 5, where_clause
        )

        # A フォールバック: フィルタで結果なし → 全巻から再検索
        if not results['documents'][0]:
            print("[A] No results with chapter filter. Falling back to full search.")
            results = await asyncio.to_thread(
                _query_collection, str(hyde_query), 5, None
            )

        context_chunks = results['documents'][0]
        context_metadatas = results['metadatas'][0]

    except Exception as e:
        print(f"[Search] Primary search failed: {e}")
        try:
            # 完全フォールバック: オリジナルの悩みテキストで検索
            results = await asyncio.to_thread(
                _query_collection, effective_concern, 5, None
            )
            context_chunks = results['documents'][0]
            context_metadatas = results['metadatas'][0]
        except Exception as e2:
            print(f"[Search] Fallback search also failed: {e2}")
            context_chunks = []
            context_metadatas = []

    # ── Phase 3: Re-ranking + CRAG ──────────────────────────────────────────

    ranked_metas: list[dict] = context_metadatas[:3]

    if reranker and len(context_chunks) > 1:
        try:
            # Re-ranking: Cross-Encoderでクエリと各チャンクのペアを精密スコアリング
            pairs = [[concern, chunk] for chunk in context_chunks]
            scores = await asyncio.to_thread(reranker.predict, pairs)

            # スコア降順でソートし上位3件を選択
            ranked = sorted(
                zip(scores, context_chunks, context_metadatas),
                key=lambda x: x[0],
                reverse=True
            )
            top3 = ranked[:3]
            context_chunks = [chunk for _, chunk, _ in top3]
            ranked_metas = [meta for _, _, meta in top3]

            # B: CRAG — Cross-Encoderスコアで検索品質を評価（追加LLM呼び出し不要）
            # ms-marco スコア目安: >3=高関連, 0〜3=中程度, <-2=低品質
            max_score = float(max(scores))
            print(f"[Re-ranking] Applied. Top Cross-Encoder score: {max_score:.2f}")

            if max_score < -2.0:
                # B: CRAG 是正処理 — 低品質な検索結果を検知し条件を広げて再検索
                # 論文: Yan et al. (2024) arXiv:2401.15884 Corrective RAG
                print(
                    f"[B-CRAG] Low retrieval quality detected (score={max_score:.2f}). "
                    "Corrective search without filter..."
                )
                fallback_results = await asyncio.to_thread(
                    _query_collection, effective_concern, 5, None
                )
                context_chunks = fallback_results['documents'][0][:3]
                ranked_metas = fallback_results['metadatas'][0][:3]
            else:
                print(f"[B-CRAG] Quality OK (score={max_score:.2f}). Proceeding.")

        except Exception as e:
            print(f"[Re-ranking] Failed: {e}")
            context_chunks = context_chunks[:3]
            ranked_metas = context_metadatas[:3]
    else:
        context_chunks = context_chunks[:3]
        ranked_metas = context_metadatas[:3]

    # ── Phase 4: Parent-Child Context Construction ──────────────────────────

    # D: Parent-Child Chunking — 検索でヒットした子チャンクの代わりに
    # メタデータに保存された親チャンク（500文字）をLLMに渡す。
    # 子チャンク(200文字)より豊富な文脈を提供し、生成品質を向上させる。
    # 論文: LlamaIndex Parent Document Retriever (2023) / Gao et al. 2023 §3.1
    parent_chunks = [
        meta.get("parent_content", chunk)
        for meta, chunk in zip(ranked_metas, context_chunks)
    ]
    context_text = (
        "\n\n".join(parent_chunks) if parent_chunks else "(No context available)"
    )

    # ── Phase 5: LLM Generation ─────────────────────────────────────────────

    generated_data: dict = {}
    try:
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
        # E: Non-blocking LLM call
        response = await asyncio.to_thread(model.generate_content, prompt)

        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()

        generated_data = json.loads(text_response)

    except Exception as e:
        print(f"[Gemini] Generation failed: {e}")
        # Fallback dummy data
        generated_data = {
            "character": "Hikaru Genji",
            "message": (
                "Because GCP API (Vertex AI) settings are invalid or unauthorized, "
                "a temporary message is displayed. I understand your concerns well."
            ),
            "explanation": (
                "Failed to search The Tale of Genji and generate text due to a "
                "configuration error. Please enable the API in your GCP project."
            ),
            "waka": "秋の夜の 月の光は 清けれど 悩める心 照らしきれずや",
            "waka_translation": (
                "The moonlight on an autumn night is pure, "
                "but it seems unable to illuminate your troubled heart."
            ),
            "image_prompt": (
                "A beautiful Japanese Heian period scroll painting showing "
                "a modern person consulting with Prince Genji under the moonlight."
            ),
        }

    # ── Phase 6: Image Generation ────────────────────────────────────────────

    image_url = ""
    try:
        from vertexai.preview.vision_models import ImageGenerationModel
        import uuid

        image_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")

        image_prompt = generated_data.get(
            "image_prompt", "A beautiful Japanese Heian period scroll painting."
        )

        # E: Non-blocking Imagen call
        images = await asyncio.to_thread(
            lambda: image_model.generate_images(
                prompt=image_prompt,
                number_of_images=1,
                aspect_ratio="16:9"
            )
        )

        filename = f"gen_{uuid.uuid4().hex}.png"
        filepath = os.path.join("static", filename)
        images[0].save(filepath, include_generation_parameters=False)

        image_url = f"http://127.0.0.1:8000/static/{filename}"
        print(f"[Imagen] Successfully generated and saved: {filepath}")

    except Exception as e:
        print(f"[Imagen] Generation failed, attempting fallback: {e}")
        # Placeholder image
        image_url = (
            "https://images.unsplash.com/photo-1545161252-78d10ed73775"
            "?q=80&w=1000&auto=format&fit=crop"
        )

    # ── Phase 7: Update Session History ──────────────────────────────────────

    # C: Multi-turn — 今回の応答を履歴に保存
    session_history[session_id].append({
        "concern": concern,
        "character": generated_data.get("character", ""),
        "message": generated_data.get("message", "")[:100],
    })
    # 最大10ターンを保持し、古いものから削除
    if len(session_history[session_id]) > 10:
        session_history[session_id].pop(0)

    return ConsultResponse(
        character=generated_data.get("character", "Unknown"),
        message=generated_data.get("message", "An error occurred."),
        explanation=generated_data.get("explanation", ""),
        waka=generated_data.get("waka", ""),
        waka_translation=generated_data.get("waka_translation", ""),
        image_url=image_url,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
