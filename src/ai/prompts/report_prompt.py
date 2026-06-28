from langchain_core.prompts import ChatPromptTemplate

report_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a CISO (Chief Information Security Officer) presenting an Executive Summary.
    You will be provided with an aggregated list of digital assets, their categories, and their risk scores.
    
    Your task:
    1. Write a professional, high-level Executive Summary in Markdown format.
    2. Highlight any critical risks (scores > 80).
    3. Provide a brief breakdown of asset categories.
    4. Keep it concise, no more than 3 paragraphs.
    
    Do NOT invent data. Only use the data provided. If there are no assets, state that the environment is empty."""),
    ("human", "Here is the raw asset data:\n\n{asset_data}")
])
