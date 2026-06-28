from langchain_core.prompts import ChatPromptTemplate

enrichment_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a Cybersecurity Asset Categorization Engine.
    Your job is to read an asset's type, value, and tags, and place it into exactly ONE high-level category.
    
    Examples of Categories:
    - Web Property (domains, websites)
    - Network Infrastructure (IPs, routers)
    - Cloud Infrastructure (AWS, Azure assets)
    - Unknown (if there isn't enough info)
    
    Output MUST perfectly match the requested JSON schema."""),
    ("human", "Asset Type: {type}\nAsset Value: {value}\nTags: {tags}")
])
