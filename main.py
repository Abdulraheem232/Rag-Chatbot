import streamlit as st
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
import os
import dotenv
from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA

dotenv.load_dotenv()

st.title("RAG Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    st.chat_message(message["role"]).markdown(message["content"])

@st.cache_resource
def get_vectorstore():
    pdf_name = "Java Notes.pdf"
    loader = PyPDFLoader(pdf_name)
    documents = loader.load()
    
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    texts = text_splitter.split_documents(documents)
    
    # Create embeddings and vectorstore
    embeddings = HuggingFaceBgeEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    vectorstore = FAISS.from_documents(texts, embeddings)
    return vectorstore

# System prompt template
system_prompt = """You are an intelligent assistant that strictly answers questions based only on the provided context.

Follow these rules:
- Answer ONLY using the provided context
- If the answer isn't in the context, say "I cannot answer this based on the document"
- Be concise and factual
- No greetings or filler text
- Cite relevant page numbers when possible

Context: {context}

Question: {question}"""

# Initialize components
vectorstore = get_vectorstore()
llm = ChatGroq(
    temperature=0,
    groq_api_key=os.environ["API_KEY"],
    model_name="llama3-8b-8192"
)

# Create QA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
    chain_type_kwargs={
        "prompt": ChatPromptTemplate.from_template(system_prompt)
    },
    return_source_documents=True
)

# Chat input
prompt = st.chat_input("Ask about the document: ")

if prompt:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)
    
    try:
        # Get response
        result = qa_chain({"query": prompt})
        response = result["result"]
        
        # Add sources if available
        if "source_documents" in result:
            sources = "\n\nSources:\n" + "\n".join(
                f"Page {doc.metadata['page']+1}" 
                for doc in result["source_documents"]
            )
            response += sources
        
        # Display and store response
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").markdown(response)
        
    except Exception as e:
        error_msg = "Sorry, I encountered an error processing your request."
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        st.chat_message("assistant").markdown(error_msg)
        st.error(f"Error: {str(e)}")