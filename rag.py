
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.prompts import PromptTemplate


VECTOR_DIR =  "vectorstore"

HOLIDAY_KEYWORDS = [
    "holiday", "holidays", "calendar", "floater", "public holiday"
]

LIGIBILITY_KEYWORDS = [
    "can i", "eligible", "entitled", "allowed",
    "apply for", "does it apply", "in case of"
]

NUMERIC_KEYWORDS = [
    "amount", "maximum", "limit", "bonus",
    "reimbursement", "₹", "rs", "rupees", "%"
]

ENTITLEMENT_KEYWORDS = [
    "how many", "total number", "number of",
    "entitlement", "per year", "leaves"
]

def is_entitlement_query(question: str) -> bool:
    q = question.lower()
    return any(k in q for k in ENTITLEMENT_KEYWORDS)

def is_eligibility_query(question: str) -> bool:
    q = question.lower()
    return any(k in q for k in ELIGIBILITY_KEYWORDS)

def is_numeric_query(question: str) -> bool:
    q = question.lower()
    return any(k in q for k in NUMERIC_KEYWORDS)

def is_holiday_query(question: str) -> bool:
    q = question.lower()
    return any(k in q for k in HOLIDAY_KEYWORDS)

def ask_policy_question(question: str):
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    vectordb = Chroma(
        persist_directory=VECTOR_DIR,
        embedding_function=embeddings
    )

    # 🔑 ROUTING LOGIC
    if is_holiday_query(question):
        retriever = vectordb.as_retriever(
            search_kwargs={
                "k": 20,
                "filter": {"department": "Holiday"}
            }
        )

    elif is_numeric_query(question):
        retriever = vectordb.as_retriever(
            search_kwargs={"k": 3}
        )

    elif is_entitlement_query(question):
        retriever = vectordb.as_retriever(
            search_kwargs={
                "k": 8,
                "filter": {"department": "Leave"}
        }
    )

    else:
        retriever = vectordb.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 6, "lambda_mult": 0.4}
        )

    llm = ChatOllama(
        model="mistral-small3.2:latest",
        temperature=0.0
    )


    prompt = PromptTemplate(
        template="""
    You are an internal Caizin company policy assistant.

    CRITICAL RULES:
    - Answer ONLY using the provided context.
    - Do NOT assume eligibility.
    - When a policy defines an explicit list (e.g. spouse, parent, child, sibling):
    - Treat the list as CLOSED.
    - If the user is NOT eligible for a specific leave:
    - Clearly state the ineligibility and the reason.
    - Then list other leave types that are defined in the policy,
        WITHOUT assuming the user qualifies for them.
    - Do NOT invent leave categories.
    - For numeric values, copy them EXACTLY as written.
    - If no alternatives are mentioned in the policy, state that explicitly.

    Context:
    {context}

    Question:
    {question}

    Answer (policy-compliant and helpful):
    """,
        input_variables=["context", "question"]
    )


    docs = retriever.get_relevant_documents(question)
    context = "\n\n".join(d.page_content for d in docs)

    return llm.invoke(prompt.format(context=context, question=question)).content

if __name__ == "__main__":
    while True:
        q = input("\nAsk a Caizin policy question (or 'exit'): ")
        if q.lower() == "exit":
            break
        print("\nAnswer:\n", ask_policy_question(q))
