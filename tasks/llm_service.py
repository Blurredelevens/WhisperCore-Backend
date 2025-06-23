from groq import Groq
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
import os
import tiktoken

class LLMService:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.MAX_TOKENS = 20000
        self.RESERVED_TOKENS = 512
        self.embedding = HuggingFaceEmbeddings()
        self.vectorstore = None
        self.qa_chain = None
        self.initialize_vectorstore()

    def initialize_vectorstore(self):
        try:
            self.vectorstore = Chroma(
                persist_directory="doc_db",
                embedding_function=self.embedding
            )
            retriever = self.vectorstore.as_retriever()
            llm = ChatGroq(
                model="llama3-8b-8192",
                temperature=0.2
            )
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
        except Exception as e:
            print(f"Error initializing vectorstore: {e}")

    def process_query(self, query):
        if not self.qa_chain:
            return {"error": "Knowledge base not initialized"}

        try:
            retrieved_docs = self.vectorstore.as_retriever().get_relevant_documents(query)
            if not retrieved_docs:
                return {"error": "No relevant documents found"}

            context = retrieved_docs[0].page_content[:20000]
            tokenized_context = self.tokenizer.encode(context)
            
            if len(tokenized_context) > self.MAX_TOKENS - self.RESERVED_TOKENS:
                context = self.tokenizer.decode(tokenized_context[:self.MAX_TOKENS - self.RESERVED_TOKENS])

            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Context: {context}\n\nQuery: {query}"}
                ],
                temperature=0.2,
                max_tokens=1024,
                stream=False
            )

            return {"data": response.choices[0].message.content}

        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}
