"""
LLM Agent with RAG Tool Integration

This module defines the customer support agent that uses a Language Model
with Retrieval-Augmented Generation (RAG) capabilities.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import os
import inspect
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate


class BaseAgent(ABC):
    """
    Abstract base class for LLM agents.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent.

        Args:
            config: Configuration dictionary containing LLM settings, prompts, etc.
        """
        self.config = config or {}
        self.is_initialized = False
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent with LLM and tools."""
        pass

    @abstractmethod
    async def process_query(self, text: str, **kwargs) -> str:
        """
        Process a text query and return a response.

        Args:
            text: Input text from the user
            **kwargs: Additional context or parameters

        Returns:
            str: Agent's response
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass


class CustomerSupportAgent(BaseAgent):
    """
    Customer Support Agent implementation using LangChain ReAct agent.

    This agent uses a Language Model with RAG capabilities to answer
    customer support queries by retrieving relevant information from
    a knowledge base.
    """

    # Keywords that indicate the user wants to speak with a human agent
    ESCALATION_KEYWORDS = [
        "speak to a manager", "human agent", "speak to someone",
        "representative", "real person", "escalate", "supervisor",
        "speak to a human"
    ]

    # Distance threshold above which retrieved results are considered
    # not relevant enough to answer from (tuned from real eval:
    # in-domain queries scored 0.499-1.303, out-of-scope scored 1.915)
    DISTANCE_THRESHOLD = 1.5

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.llm = None
        self.agent = None
        self.agent_executor = None
        self.knowledge_base = None

    async def initialize(self) -> None:
        """
        Initialize the customer support agent: LLM, knowledge base, tools, agent executor.
        """
        # Prefer Groq (fast inference). Falls back to OpenAI, then RAG-only if neither is set.
        groq_api_key = self.config.get("groq_api_key") or os.getenv("GROQ_API_KEY")
        openai_api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

        if groq_api_key and not str(groq_api_key).startswith("your_"):
            try:
                from langchain_groq import ChatGroq
                self.llm = ChatGroq(
                    groq_api_key=groq_api_key,
                    model_name=os.getenv("GROQ MODEL", "llama-3.1-8b-instant"),
                    temperature=float(self.config.get("temperature", 0.2)),
                )
                print("Groq LLM initialized successfully.")
            except Exception as exc:
                print(f"Groq LLM disabled; falling back to RAG-only mode: {exc}")
                self.llm = None
        elif openai_api_key and not str(openai_api_key).startswith("your_"):
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    api_key=openai_api_key,
                    model=self.config.get("model", "gpt-3.5-turbo"),
                    temperature=float(self.config.get("temperature", 0.2)),
                )
            except Exception as exc:
                print(f"OpenAI LLM disabled; falling back to RAG-only mode: {exc}")
                self.llm = None
        else:
            self.llm = None

        # Initialize knowledge base
        await self._setup_knowledge_base()

        # Create tools including RAG tool
        tools = await self._create_tools()

        # Create the ReAct agent only when an LLM is configured.
        await self._create_agent(tools)

        self.is_initialized = True

    async def _setup_knowledge_base(self) -> None:
        """
        Set up the knowledge base for RAG using ChromaDB.
        """
        try:
            import chromadb
            
            import os
            import hashlib

            # Initialize ChromaDB (persistent storage)
            db_path = "./data/chroma_db"
            os.makedirs(db_path, exist_ok=True)

            self.chroma_client = chromadb.PersistentClient(path=db_path)

            # Collection name
            collection_name = "customer_support_kb"

            # Check if collection already exists and has data
            try:
                self.collection = self.chroma_client.get_collection(collection_name)
                if self.collection.count() > 0:
                    print(f"Knowledge base already exists with {self.collection.count()} documents")
                    return
            except Exception:
                # Collection doesn't exist, create it
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Customer support knowledge base"}
                )

            # Load predefined customer support documents
            knowledge_documents = self._get_customer_support_documents()

            

            # Process and store documents
            print(f"Ingesting {len(knowledge_documents)} documents into knowledge base...")

            documents = []
            metadatas = []
            ids = []

            for i, doc_data in enumerate(knowledge_documents):
                doc_id = f"doc_{i}_{hashlib.md5(doc_data['content'].encode()).hexdigest()[:8]}"

                documents.append(doc_data['content'])
                metadatas.append({
                    'category': doc_data['category'],
                    'title': doc_data['title'],
                    'doc_id': doc_id
                })
                ids.append(doc_id)

            # Add documents to ChromaDB (it will automatically create embeddings)
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            print(f"Successfully ingested {len(documents)} documents into ChromaDB")

        except Exception as e:
            print(f"Error setting up knowledge base: {str(e)}")
            raise

    def _get_customer_support_documents(self) -> List[Dict[str, str]]:
        """
        Predefined customer support knowledge base.
        """
        return [
            # Return Policy
            {
                "title": "Return Policy Overview",
                "category": "returns",
                "content": "We offer a 30-day return policy for all products purchased from our store. Items must be in original condition with all tags and packaging intact. Returns are processed within 5-7 business days of receiving the returned item. Refunds are issued to the original payment method."
            },
            {
                "title": "Return Process Steps",
                "category": "returns",
                "content": "To initiate a return: 1) Log into your account and go to Order History, 2) Select the order and click 'Return Items', 3) Choose the items to return and reason, 4) Print the prepaid return label, 5) Pack items securely and attach the label, 6) Drop off at any UPS location or schedule pickup."
            },
            {
                "title": "Non-Returnable Items",
                "category": "returns",
                "content": "The following items cannot be returned: personalized or customized products, perishable goods, digital downloads, gift cards, intimate apparel, and items marked as final sale. Health and safety regulations prevent returns of opened cosmetics and personal care items."
            },

            # Shipping Information
            {
                "title": "Shipping Methods and Times",
                "category": "shipping",
                "content": "We offer multiple shipping options: Standard shipping (5-7 business days, free on orders over $50), Express shipping (2-3 business days, $12.99), Next-day shipping (1 business day, $24.99). All orders placed before 2 PM EST ship the same day."
            },
            {
                "title": "International Shipping",
                "category": "shipping",
                "content": "We ship internationally to over 50 countries. International shipping takes 7-14 business days via DHL Express. Shipping costs vary by destination and are calculated at checkout. Customers are responsible for customs fees and import duties. Some restrictions apply to certain products and countries."
            },
            {
                "title": "Order Tracking",
                "category": "shipping",
                "content": "Once your order ships, you'll receive a tracking number via email. Track your package using the tracking number on our website or the carrier's website. You can also track orders by logging into your account and viewing Order History. Tracking updates may take 24 hours to appear."
            },

            # Customer Support
            {
                "title": "Contact Information",
                "category": "support",
                "content": "Customer support is available 24/7 via multiple channels: Phone: 1-800-HELP-NOW (1-800-435-7669), Email: support@company.com, Live chat on our website (available 6 AM - 12 AM EST), or submit a support ticket through your account dashboard."
            },
            {
                "title": "Response Times",
                "category": "support",
                "content": "Our support team response times: Live chat - immediate during business hours, Phone support - average wait time under 3 minutes, Email support - response within 4 hours during business days, Support tickets - response within 24 hours. Premium customers receive priority support with faster response times."
            },

            # Warranty and Technical Support
            {
                "title": "Product Warranty",
                "category": "warranty",
                "content": "All products come with a manufacturer's warranty. Electronics have 1-year warranty covering defects and malfunctions. Apparel and accessories have 90-day warranty against material defects. Warranty claims require proof of purchase and must be initiated within the warranty period."
            },
            {
                "title": "Technical Support",
                "category": "technical",
                "content": "Free technical support is available for all electronic products. Our certified technicians provide assistance with setup, troubleshooting, and software issues. Technical support is available Monday-Friday 8 AM - 8 PM EST via phone or email. We also offer remote assistance for compatible devices."
            },

            # Account and Orders
            {
                "title": "Account Management",
                "category": "account",
                "content": "Manage your account online: Update personal information and addresses, view order history and tracking, manage payment methods, set communication preferences, download invoices and receipts. Account changes may take up to 24 hours to reflect across all systems."
            },
            {
                "title": "Order Modifications",
                "category": "orders",
                "content": "Orders can be modified or canceled within 1 hour of placement if not yet processed. Contact customer service immediately to make changes. Once an order is processed and shipped, it cannot be modified. You can return unwanted items following our return policy."
            },

            # Payment and Billing
            {
                "title": "Payment Methods",
                "category": "payment",
                "content": "We accept all major credit cards (Visa, MasterCard, American Express, Discover), PayPal, Apple Pay, Google Pay, and Buy Now Pay Later options through Klarna and Afterpay. Gift cards and store credit can also be used for purchases. Payment is processed securely using 256-bit SSL encryption."
            },
            {
                "title": "Billing and Invoices",
                "category": "billing",
                "content": "Billing occurs when your order ships. You'll receive an email confirmation with invoice details. Invoices are available in your account under Order History. For business purchases, we can provide detailed invoices with tax information. Contact our billing department for any payment disputes or questions."
            },

            # Product Information
            {
                "title": "Product Availability",
                "category": "products",
                "content": "Product availability is updated in real-time on our website. If an item shows as 'In Stock', it's available for immediate shipping. 'Limited Stock' means fewer than 10 items remaining. 'Pre-order' items will ship on the specified release date. Out of stock items can be added to your wishlist for restock notifications."
            },
            {
                "title": "Size and Fit Guide",
                "category": "products",
                "content": "Each product page includes detailed size charts and fit information. For apparel, we recommend checking measurements against our size guide rather than relying on size labels from other brands. If you're between sizes, we generally recommend sizing up. Our customer service team can provide personalized fit recommendations."
            }
        ]

    async def _create_tools(self) -> List[Tool]:
        """
        Create tools for the agent, including the RAG tool.

        Returns:
            List[Tool]: List of tools available to the agent
        """
        tools = []

        rag_tool = Tool(
            name="knowledge_search",
            description="Search the customer support knowledge base for relevant information",
            func=lambda query:"Error: sync call not supported,use async",
            coroutine=self._rag_search
        )
        tools.append(rag_tool)

        return tools

    async def _rag_search(self, query: str) -> str:
        """
        Retrieve relevant documents from ChromaDB, apply the out-of-scope
        distance threshold, and format the results.

        Args:
            query: Search query from the user (e.g., "What is your return policy?")

        Returns:
            str: Formatted relevant information from the knowledge base,
                 or the sentinel "__NO_RELEVANT_MATCH__" if nothing relevant
                 was found (handled by process_query).
        """
        if not hasattr(self, 'collection') or self.collection is None:
            return "Knowledge base not available. Please ensure the service is properly initialized."

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=3,
                include=["documents", "metadatas", "distances"],
            )

            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            if not documents:
                return "I could not find relevant customer support information for that question."

            # Out-of-scope threshold check
            if distances[0] > self.DISTANCE_THRESHOLD:
                return "__NO_RELEVANT_MATCH__"

            formatted_results = []
            for doc, meta, distance in zip(documents, metadatas, distances):
                title = meta.get("title", "Customer Support Info")
                category = meta.get("category", "general")
                formatted_results.append(
                    f"**{title}** ({category}, relevance distance: {distance:.3f})\n{doc}"
                )

            return "\n\n".join(formatted_results)

        except Exception as e:
            return f"Error searching knowledge base: {str(e)}"

    def _check_escalation_intent(self, text: str) -> bool:
        """Checks if the query indicates the user wants to speak with a human."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.ESCALATION_KEYWORDS)

    async def _create_agent(self, tools: List[Tool]) -> None:
        """
        Create the ReAct agent.

        Args:
            tools: List of tools available to the agent
        """
        prompt_template = """
        You are a helpful customer support agent. Use the available tools to assist customers.

        You have access to the following tools:
        {tools}

        Use the following format:

        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question

        Question: {input}
        Thought: {agent_scratchpad}
        """

        prompt = PromptTemplate.from_template(prompt_template)

        if self.llm is None:
            self.agent = None
            self.agent_executor = None
            return

        self.agent = create_react_agent(self.llm, tools, prompt)
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=tools,
            verbose=bool(self.config.get("verbose",False)),
            handle_parsing_errors=True,
            max_iterations=5,
        )

    async def process_query(self, text: str, **kwargs) -> str:
        """
        Process user query using the agent, with escalation detection
        and out-of-scope fallback handling.

        Args:
            text: User's query
            **kwargs: Additional context

        Returns:
            str: Agent's response
        """
        if not self.is_initialized:
            raise RuntimeError("Agent not initialized")

        if not text or not text.strip():
            return "Please ask a customer support question so I can help."

        # Escalation check runs BEFORE retrieval
        if self._check_escalation_intent(text):
            return (
                "It sounds like you'd like to speak with a human support agent. "
                "I'm connecting you now - a representative will be with you shortly. "
                "In the meantime, is there anything I can look up for you?"
            )
         # Out-of-scope pre-check runs BEFORE the agent, so the agent never
         # wastes iterations trying to answer something with no relevant context
        precheck_context = await self._rag_search(text)
        if precheck_context == "__NO_RELEVANT_MATCH__":
           return (
            "I couldn't find relevant information to answer that. "
            "Could you rephrase your question, or would you like to speak "
            "with a human support agent?"
            )    

        # Use the full LangChain agent when an LLM/API key is available.
        if self.agent_executor is not None:
            result = await self.agent_executor.ainvoke({"input": text})
            return result.get("output", str(result))

        # RAG-only fallback: returns a concise answer grounded in the KB.
        context = await self._rag_search(text)

        # Handle no-match sentinel
        if context == "__NO_RELEVANT_MATCH__":
            return (
                "I couldn't find relevant information to answer that. "
                "Could you rephrase your question, or would you like to speak "
                "with a human support agent?"
            )

        return (
            "Here is the relevant customer support information I found:\n\n"
            f"{context}\n\n"
            "Let me know if you need help with the next step."
        )

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        self.llm = None
        self.agent = None
        self.agent_executor = None
        self.is_initialized = False