import os
import uuid
import logging
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from openai import APITimeoutError, APIConnectionError, RateLimitError

from src.ai.tools.database_tools import build_database_tools

logger = logging.getLogger(__name__)

def execute_query(query: str, db: Session, tenant_id: uuid.UUID) -> str:
    """
    Orchestrates the LangChain agent to answer a user's natural language query.
    Implements mandatory data retrieval and graceful fallbacks for LLM failures.
    """
    
    # 1. Setup the LLM
    try:
        # Note: We expect OPENAI_API_KEY to be in the environment.
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0, # Strict, non-creative answers
            request_timeout=15.0, # Graceful timeout
            max_retries=1
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return "System Error: Unable to initialize AI service."

    # 2. Bind the tools securely to the tenant
    tools = build_database_tools(db, tenant_id)

    # 3. Create the strictly-grounded prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the DarkAtlas AI Security Assistant.
        Your ONLY job is to answer questions about the user's digital assets.
        
        CRITICAL RULES:
        1. You MUST use the provided tools to retrieve data from the database before answering.
        2. NEVER rely on your internal knowledge. If the tools return no data, say you don't know.
        3. Do not invent or hallucinate assets.
        4. Provide concise, direct answers."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])

    # 4. Create and run the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    try:
        result = agent_executor.invoke({"input": query})
        return result["output"]
        
    # 5. Constitution: Graceful Fallbacks
    except APITimeoutError:
        logger.warning("OpenAI API Timeout")
        return "The AI service is currently taking too long to respond. Please try again later."
    except RateLimitError:
        logger.warning("OpenAI API Rate Limited")
        return "We have hit our AI request limit. Please try again in a few moments."
    except APIConnectionError:
        logger.warning("OpenAI API Connection Error")
        return "Could not connect to the AI service. Please check your network connection."
    except Exception as e:
        logger.error(f"Unexpected error during AI execution: {e}")
        return "An unexpected error occurred while processing your query."
