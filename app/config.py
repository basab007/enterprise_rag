import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_ID=os.getenv("PROJECT_ID","enterprise-rag")
    import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- GCP Core ---
    PROJECT_ID = os.getenv("PROJECT_ID", "enterprise-rag-513418")
    LOCATION = os.getenv("LOCATION", "us-central1")
    GCP_DOC_AI_LOCATION = os.getenv("GCP_DOC_AI_LOCATION", "us")
    GCP_DOC_AI_PROCESSOR_ID = os.getenv("GCP_DOC_AI_PROCESSOR_ID","6592be50eef46b21" )
     
    RAW_BUCKET = os.getenv("GCP_RAW_BUCKET", "enterprise-rag-513418-raw")
    PROCESSED_BUCKET = os.getenv("GCP_PROCESSED_BUCKET", "enterprise-rag-513418-processed")

    # --- Vector DB (Qdrant) ---
    QDRANT_URL = os.getenv("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION = "enterprise_rag"

    # --- LLM (Groq) ---
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    #GROQ_FALLBACK_API_KEY = os.getenv("GROQ_FALLBACK_API_KEY")
    GROQ_MODEL = "qwen/qwen3.8-27b"


    # --- Observability ---
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true")
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "Enterprise_Rag")
    LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

   


# Apply LangSmith env vars for automatic LangChain tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "Enterprise_Rag")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

settings = Settings()


