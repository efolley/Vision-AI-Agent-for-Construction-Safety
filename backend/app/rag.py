import os
import json
import pathlib
from typing import List, Dict
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter


class RAGVectorDBManager:
    def __init__(self, 
                 persist_dir: str = str(pathlib.Path(__file__).parent.parent / "RAG_vectorDB")):
        self.persist_dir = persist_dir
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.db = None
        self._load_or_create()


    def _load_or_create(self):
        if os.path.exists(self.persist_dir):
            print(f"Loading existing vector DB from {self.persist_dir}")
            self.db = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
        else:
            print(f"No DB found. Creating new one at {self.persist_dir}")
            self.db = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)


    def add_violations_from_json(self, json_path: str):
        """Add or update violations from a JSON file (like your common_osha_violations.json)"""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"File not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        texts = []
        metadatas = []

        for item in data:
            text = item.get("text", "")
            if not text:
                continue
            texts.append(text)
            metadatas.append({
                "code": item.get("id", "unknown"),
                "title": item.get("title", "No title"),
                "source": os.path.basename(json_path)
            })

        print(f"Adding {len(texts)} violations to vector DB...")
        self.db.add_texts(texts=texts, metadatas=metadatas)
        print("Done! Vector DB updated.")


    def add_raw_texts(self, texts: List[str], metadatas: List[Dict] = None):
        """Add any custom list of texts"""
        if metadatas is None:
            metadatas = [{}] * len(texts)
        self.db.add_texts(texts=texts, metadatas=metadatas)
        print(f"Added {len(texts)} custom entries.")


    def get_retriever(self, k: int = 3):
        return self.db.as_retriever(search_kwargs={"k": k})


    def reset_db(self):
        """Delete everything and start fresh"""
        if os.path.exists(self.persist_dir):
            import shutil
            shutil.rmtree(self.persist_dir)
            print("Old DB deleted.")
        self._load_or_create()
        print("Fresh DB ready.")