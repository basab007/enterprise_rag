import time
import logfire


from flashrank import Ranker,RerankRequest


_ranker=None


def _get_ranker()->Ranker:
    global _ranker
    if _ranker is None:
        try:
            logfire.info("🧠 Initializing FlashRank Model (TinyBERT) locally...")
            _ranker=Ranker(cache="/tmp/flashrank_cache")
        except Exception:
            _ranker = Ranker()
    return _ranker


def rerank_documents(query: str, documents: list[str], top_n: int = 5) -> list[str]:
     if not documents:
        return []
     start_time = time.time()
     logfire.info(f"📡 [Reranker] Sending {len(documents)} docs to FlashRank Cross-Encoder...")

     try :
         rank = _get_ranker()
         
         passages=[

            {id:i,"text":doc}
            for i,doc in enumerate(documents)

        ]


         request=RerankRequest(query,passages)
         results=_ranker.rerank(request)
         reranked_docs = []
         for res in results[:top_n]:
            reranked_docs.append(res['text'])

         duration = time.time() - start_time
         top_score = results[0]['score'] if results else 'N/A'
         logfire.info(f"✅ [Reranker] Done in {duration:.2f}s. Top semantic score: {top_score}")
        
         return reranked_docs

     except Exception as e:
        logfire.error(f"❌ [Reranker] Semantic Reranking Failed: {e}")
        # Fallback to the original Qdrant order to ensure the user still gets an answer
        return documents[:top_n]



