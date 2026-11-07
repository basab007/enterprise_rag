import os
import sys
import uuid
import json
import tempfile
import logfire
import vertexai

from typing import List
from fastapi import FastAPI, Request, BackgroundTasks
from google.cloud import storage
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import settings
from app.services.retrieval.embedding import embed_texts
from app.ingestion.loaders.pdf import parse_pdf
from app.ingestion.loaders.html import parse_html
from app.ingestion.loaders.text import parse_text
from app.ingestion.chunking.splitter import chunk_text

logfire.configure(service_name="enterprise-ingestion-service")
vertexai.init(project=settings.PROJECT_ID,location=settings.LOCATION)
storage_client=storage.Client(project=settings.PROJECT_ID)

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)


def upload_to_gcs(data,bucket_name:str,destination_blob_name:str,is_json:bool=False):
    with logfire.span("☁️ GCS Upload",bucket=bucket_name,blob=destination_blob_name):
        try:
            bucket=storage_client.bucket(bucket_name)
            blob=bucket.blob(destination_blob_name)
            if is_json:
                blob.upload_from_string(json.dumps(data),content_type="application/json")
            else:
                blob.upload_from_file(data)
            logfire.info(f"✅ Uploaded to {bucket_name}/{destination_blob_name}")
        except Exception as e:
            logfire.error(f"❌ Failed to upload to GCS: {e}")
            raise 
def _ensure_collection():
    if not qdrant_client.collection_exists(settings.QDRANT_COLLECTION):
        qdrant_client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=768,distance=models.Distance.COSINE)
        )
    logfire.info(f"🆕 Created Qdrant collection '{settings.QDRANT_COLLECTION}'")


def process_file(file_path: str, filename: str, source_type: str, skip_raw_upload: bool = False):
    with logfire.span("🚀 Processing File", file=filename, source=source_type,
                      cloud_mode=skip_raw_upload):
        try:
            _ensure_collection()
            raw_gcs_path=f"{source_type}/{filename}"
            if not skip_raw_upload:
                upload_to_gcs(file_path,settings.RAW_BUCKET_NAME,raw_gcs_path)
            else:
                logfire.info(f"⏩ Skipping RAW upload (cloud mode) — file already at gs://{settings.RAW_BUCKET}/{raw_gcs_path}")


            ext=filename.split(".")[-1].lower()
             # Step 2: Extract text
            ext = filename.lower().split(".")[-1]
            if ext == "pdf":
                full_text = parse_pdf(file_path)
            elif ext in ("html", "htm"):
                full_text = parse_html(file_path)
            elif ext == "txt":
                full_text = parse_text(file_path)
            elif ext in ("docx", "pptx"):
                from app.ingestion.loaders.office import parse_office
                full_text = parse_office(file_path)
            else:
                logfire.warning(f"⏩ Skipping unsupported file type: {filename}")
                return
            if not full_text or not full_text.strip():
                logfire.warning(f"⚠️ No text extracted from {filename}")
                return

            # Step 3: Chunk
            chunks = chunk_text(full_text)
            if not chunks:
                return


            processed_data={"filename": filename,  "chunks": chunks,"source_type": source_type}
            processed_gcs_path = f"{source_type}/{filename}.json"
            upload_to_gcs(processed_data, settings.PROCESSED_BUCKET_NAME, processed_gcs_path, is_json=True)
            with logfire.span("vectorizing and indexing"):
                embeddings=embed_texts(chunks)
                points=[

                    models.PointStruct(id=str(uuid.uuid4(),
                                              vector=vector,
                                               payload={
                            "text": chunk,
                            "source": filename,
                            "source_type": source_type,
                            "raw_gcs_path": f"gs://{settings.RAW_BUCKET}/{raw_gcs_path}",
                        },


                    ))

                    for chunk,vector in zip(chunks,embeddings)
                ]

                qdrant_client.upsert(
                    collection_name=settings.QDRANT_COLLECTION,
                    points=points
                )
        except Exception as e:
            logfire.error(f"💥 Failed to process {filename}: {e}")


def _process_from_gcs(bucket_name: str, object_name: str, filename: str, source_type: str):
    with logfire.span("☁️ Cloud Mode: Download & Process", file=object_name):
        try:
            ext=filename.lower().split(".")[-1]
            with tempfile.NamedTemporaryFile(suffix=f".{ext}",delete=False) as tmp:
                tmp_path=tmp.name


            bucket=storage_client.bucket(bucket_name)
            blob=bucket.blob(object_name)
            blob.download_to_filename(tmp_path)
            logfire.info(f"⬇️ Downloaded gs://{bucket_name}/{object_name} → {tmp_path}")
            process_file(tmp_path, filename, source_type, skip_raw_upload=True)


        except Exception as e:
            logfire.error(f"❌ Cloud processing failed for {object_name}: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logfire.error(f"❌ Failed to delete temporary file {tmp_path}: {e}")

def run_universal_ingestion(base_dir: str, explicit_source_type: str = None, wipe: bool = False):
    with logfire.span("🧩 Universal Ingestion", base_dir=base_dir, explicit_source_type=explicit_source_type, wipe=wipe):
        if wipe:
            with logfire.span("🧹 Wiping Collection"):
                if qdrant_client.collection_exists(settings.QDRANT_COLLECTION):
                    qdrant_client.delete_collection(settings.QDRANT_COLLECTION)
                    logfire.info(f"🗑️ Collection '{settings.QDRANT_COLLECTION}' deleted")
                _ensure_collection()
        subdirs=[d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]



        if not subdirs:
            if explicit_source_type:
                source_type=explicit_source_type
            else:
                base_name=os.path.basename(os.path.normpath(base_dir)).lower()
                source_type = "true" if "true" in base_name else "noisy" if "noisy" in base_name else "general"
            logfire.info(f"📂 No subdirectories — processing {base_dir} as '{source_type}'")
            _process_directory(base_dir, source_type)
        else:
             for subdir in subdirs:
                source_type = "true" if "true" in subdir.lower() else "noisy" if "noisy" in subdir.lower() else subdir
                _process_directory(os.path.join(base_dir, subdir), source_type)


def _process_directory(dir_path: str, source_type: str):
    with logfire.span("📁 Scanning Directory", path=dir_path, source=source_type):
        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        logfire.info(f"🔍 Found {len(files)} files")
        for filename in files:
            process_file(os.path.join(dir_path, filename), filename, source_type, skip_raw_upload=False)


if __name__ == "__main__":
    wipe_requested = "--wipe" in sys.argv
    clean_args     = [a for a in sys.argv if a != "--wipe"]
    target_dir     = clean_args[1] if len(clean_args) > 1 else "DATA"
    explicit_type  = clean_args[2] if len(clean_args) > 2 else None

    if not os.path.exists(target_dir):
        print(f"Error: Path {target_dir} does not exist.")
        sys.exit(1)

    run_universal_ingestion(target_dir, explicit_source_type=explicit_type, wipe=wipe_requested)
    logfire.info("🏁 Universal Ingestion Job Completed")

        




    

