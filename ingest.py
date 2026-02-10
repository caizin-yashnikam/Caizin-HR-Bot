import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document

# -----------------------------
# PATHS (production safe)
# -----------------------------
DATA_DIR =  "data"
VECTOR_DIR = "vectorstore"

POLICY_FILES = {
    "Caizin POSH Policy V2- 2024.pdf": "POSH",
    "Caizin_Holiday_Calender_2026.pdf": "Holiday",
    "Caizin- Employee Referral Polcy .pdf": "HR",
    "Fitness policy- 10th Feb 2025 .pdf": "Benefits",
    "Leave Policy caizin .pdf": "Leave",
    "Performance Improvement Plan Policy - Final.pdf": "PIP",
    "Policy Copy_Employees Version.pdf": "General HR",
    "Travel & Expense Policy.pdf": "Finance"
}



def ingest():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150
    )

    all_chunks = []

    holiday_txt_path = os.path.join(DATA_DIR, "holiday_calendar_structured.txt")
    if os.path.exists(holiday_txt_path):
        with open(holiday_txt_path, "r") as f:
            holiday_text = f.read()

    holiday_doc = Document(
        page_content=holiday_text,
        metadata={
            "department": "Holiday",
            "source_file": "holiday_calendar_structured.txt"
        }
    )

    all_chunks.extend(
        splitter.split_documents([holiday_doc])
    )

    for filename, department in POLICY_FILES.items():
        file_path = os.path.join(DATA_DIR, filename)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ Missing file: {filename}")

        print(f"📄 Loading: {filename}")
        loader = PyPDFLoader(file_path)
        pages = loader.load()

        for page in pages:
            chunks = splitter.split_documents([page])

            for chunk in chunks:
                chunk.metadata.update({
                    "department": department,
                    "source_file": filename,
                    "page": page.metadata.get("page"),
                })

                # Holiday-specific enrichment
                if department == "Holiday":
                    text = chunk.page_content.lower()
                    if "floater" in text or "optional" in text:
                        chunk.metadata["holiday_type"] = "floater"
                    else:
                        chunk.metadata["holiday_type"] = "regular"

                all_chunks.append(chunk)

    print(f"✂️ Total chunks created: {len(all_chunks)}")

    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=VECTOR_DIR
    )

    print("✅ All Caizin policy documents ingested successfully")

if __name__ == "__main__":
    ingest()
