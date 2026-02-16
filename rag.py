import os
import requests
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# =========================
# CONFIG
# =========================
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

MISTRAL_KEY = os.getenv("MISTRAL_API_KEY")

# =========================
# CLIENTS
# =========================
search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_KEY),
)

azure_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-02-15-preview"
)

# =========================
# EMBEDDING
# =========================
def get_query_embedding(text):
    response = azure_client.embeddings.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        input=text
    )
    return response.data[0].embedding


# =========================
# HYBRID SEARCH
# =========================
def search_documents(query: str):
    query_embedding = get_query_embedding(query)

    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=8,
        fields="embedding"
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        top=8
    )

    docs = []
    seen = set()

    for r in results:
        content = r.get("content")
        if content and content not in seen:
            docs.append(content)
            seen.add(content)

    return docs[:12]

# =========================
# MISTRAL GENERATION
# =========================
def generate_answer(question: str, context_docs: list):
    if not context_docs:
        return "I couldn't find this in the company policy."

    context = "\n\n".join(context_docs)


    prompt = f"""
You are an internal Caizin company policy assistant.

    CRITICAL RULES:
    - Answer ONLY using the provided context.
    - Do NOT assume eligibility.
    - When a policy defines an explicit list (e.g. spouse, parent, child, sibling):
    - Treat the list as CLOSED.
    - If the user is NOT eligible for a specific leave:
    - Clearly state the ineligibility and the reason.
    - HANDLING INELIGIBILITY:
       - If the user is NOT eligible, clearly state the reason based on the text.
       - IF AND ONLY IF the user asked about a specific "Leave Type" (like Sick Leave), you may list other available leave types.
       - IF the user asked about "Benefits" or "Reimbursements" (like Gym/Fitness), DO NOT list leave types. Only mention alternative financial benefits if they exist in the text.
    - Do NOT invent leave categories.
    - For numeric values, copy them EXACTLY as written.
    - If no alternatives are mentioned in the policy, state that explicitly.
    - For final confirmation and official applicability, please verify the policy details with HR.



    Context:
    {context}

    Question:
    {question}

"""
    response = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {MISTRAL_KEY}"},
        json={
            "model": "mistral-small-latest",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0
        }
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# =========================
# MAIN ENTRY
# =========================
def ask_policy_question(question: str):
    docs = search_documents(question)
    return generate_answer(question, docs)


if __name__ == "__main__":
    question = input("Ask a policy question: ")
    answer = ask_policy_question(question)
    print("\nAnswer:\n")
    print(answer)
