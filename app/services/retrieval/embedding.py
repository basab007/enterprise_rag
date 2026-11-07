import vertexai
from vertexai.language_models import TextEmbeddingModel
from app.config import settings

model = None
BATCH_SIZE = 50 


def get_embedding_model():
    global model
    if model is None:
        vertexai.init(project=settings.PROJECT_ID,location=settings.LOCATION)
        model=TextEmbeddingModel.from_pretrained("text-embedding-004")
    return model


def embed_query(query:str):
    model=get_embedding_model()
    embedding=model.get_embeddings([query])
    return embedding[0].values

 def embed_texts(texts:list[str]):
    model=get_embedding_model()
    all_embedding=[]

    for i in range(0,len(texts),BATCH_SIZE):
        batch=texts[i:i+BATCH_SIZE]
        embedding=model.get_embedding(batch)
        all_embedding.extend([e.values for e in embedding])
    return all_embedding
        