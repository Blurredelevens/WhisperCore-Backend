from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
import os
import tiktoken
import logging
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

logger = logging.getLogger(__name__)


def configure_timeouts():
    """Configure timeouts for requests to prevent hanging downloads."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class LLMService:
    qa_chain = None
    retriever = None
    groq_client = None
    tokenizer = None
    vectorstore = None
    llm = None
    MAX_TOKENS = 20000
    RESERVED_TOKENS = 512
    
    def __init__(self):
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY environment variable is not set")
            
            # Log API key status (without exposing the actual key)
            logger.info(f"GROQ_API_KEY found: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '***'}")
            
            # Set up tokenizer
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            # Initialize embedding with a smaller, faster model and timeout configuration
            try:
                # Use a smaller model that's faster to download
                self.embedding = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                # Try with an even smaller model as fallback
                try:
                    logger.info("Trying fallback embedding model...")
                    self.embedding = HuggingFaceEmbeddings(
                        model_name="sentence-transformers/paraphrase-MiniLM-L3-v2",
                        model_kwargs={'device': 'cpu'},
                        encode_kwargs={'normalize_embeddings': True}
                    )
                    logger.info("Fallback embedding model loaded successfully")
                except Exception as fallback_error:
                    logger.error(f"Fallback embedding model also failed: {fallback_error}")
                    raise ValueError(f"Failed to initialize any embedding model: {e}")
            
            self.persist_directory = "doc_db"
            
            # Try to load existing vectorstore
            try:
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embedding
                )
                self.retriever = self.vectorstore.as_retriever()
                
                # Initialize LLM with better error handling
                logger.info("Initializing Groq LLM...")
                self.llm = ChatGroq(
                    model="llama3-8b-8192",
                    temperature=0.2
                )
                logger.info("Groq LLM initialized successfully")
                
                # Create QA chain
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=self.retriever,
                    return_source_documents=True
                )
                
                logger.info("Vectorstore and QA chain initialized successfully")
            except Exception as e:
                logger.warning(f"No existing vectorstore found: {e}")
                self.vectorstore = None
                self.retriever = None
                self.qa_chain = None
                
            logger.info("LLMService initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing LLMService: {e}")
            raise

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a query using the knowledge base and LLM.
        
        Args:
            query: The user's query string
            
        Returns:
            Dict containing the response or error information
        """
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            # Validate input
            if not query or not query.strip():
                return {"error": "Query cannot be empty"}
            
            if not self.qa_chain:
                return {"error": "No knowledge base available. Please upload a document first."}
            
            # Get relevant documents
            retrieved_docs = self.retriever.get_relevant_documents(query)
            
            # if not retrieved_docs:
                # return {"error": "No relevant documents found. Please try a different query."}
            
            # Process context
            if retrieved_docs:
                context = retrieved_docs[0].page_content
                context = context[:20000]
            else:
                context = ""
            tokenized_context = self.tokenizer.encode(context)

            max_context_tokens = self.MAX_TOKENS - self.RESERVED_TOKENS
            if len(tokenized_context) > max_context_tokens:
                truncated_tokens = tokenized_context[:max_context_tokens]
                context = self.tokenizer.decode(truncated_tokens)

            # Create final query with context
            final_query = self._get_final_query(context, query)
            tokenized_query = self.tokenizer.encode(final_query)

            if len(tokenized_query) >= self.MAX_TOKENS:
                return {"error": "The combined query and context are too long. Please refine your query."}
            
            # Get LLM response
            try:
                logger.info(f"Sending query to LLM: {final_query[:200]}...")
                response = self.llm.invoke(final_query)
                logger.info("LLM response received successfully")
            except Exception as llm_error:
                logger.error(f"LLM API call failed: {llm_error}")
                # Check if it's an API key or network issue
                if "403" in str(llm_error) or "Access denied" in str(llm_error):
                    return {"error": "API access denied. Please check your GROQ_API_KEY and network settings."}
                elif "401" in str(llm_error):
                    return {"error": "Invalid API key. Please check your GROQ_API_KEY."}
                else:
                    return {"error": f"LLM service error: {str(llm_error)}"}
            
            # Extract and validate JSON response
            try:
                response_json = response.content
                logger.info(f"Response content extracted: {str(response_json)[:200]}...")
                if isinstance(response_json, str):
                    try:
                        response_json = json.loads(response_json)
                    except Exception:
                        response_json = {"text": response_json}
            except Exception as e:
                logger.error(f"JSON extraction failed: {str(e)}")
                return {
                    "error": {
                        "type": "json_parsing_error",
                        "message": "Failed to parse LLM response",
                        "details": str(e)
                    }
                }

            if isinstance(response_json, dict) and "error" in response_json:
                logger.error(f"LLM returned error: {response_json['error']}")
                return {
                    "error": {
                        "type": "llm_error", 
                        "message": response_json['error']
                    }
                }
            elif isinstance(response_json, dict):
                logger.info("LLM returned dict response.")
                return {"data": response_json}
            elif isinstance(response_json, str):
                logger.info("LLM returned plain text response.")
                return {"data": response_json}
            else:
                logger.error(f"Unexpected response_json type: {type(response_json)}")
                return {"error": "Unexpected response type from LLM"}

            logger.info(f"Query processed successfully. Response length: {len(str(response_json))}")
            
            return {"data": response_json}
            
        except Exception as e:
            logger.error(f"Unexpected error processing query: {e}")
            return {"error": f"Error processing your query: {str(e)}"}

    def _get_final_query(self, context: str, query: str) -> str:
        """
        Create a final query with context for the LLM.
        """
        return f"""
        Context: {context}
        
        Query: {query}
        
        Please provide a detailed response based on the context above.
        """

    @staticmethod
    def get_available_models() -> list:
        """Get list of available Groq models."""
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return []
    
            groq_client = ChatGroq(api_key=api_key)
            models = groq_client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            return []

    @staticmethod
    def validate_api_key() -> bool:
        """Validate if the GROQ_API_KEY is working."""
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return False
            
            
            groq_client = ChatGroq(api_key=api_key)
            # Try a simple test call
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
                model="llama3-8b-8192",
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False