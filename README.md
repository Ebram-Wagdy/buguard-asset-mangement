# DarkAtlas: AI-Powered Asset Management System

An intelligent, multi-tenant cybersecurity asset management API. Built with FastAPI, PostgreSQL, and OpenAI.

## 🚀 Setup & Run Instructions

This application is fully containerized. You can launch the entire stack (API + PostgreSQL database) with a single command.

### Prerequisites
- Docker & Docker Compose installed and running.
- An active OpenAI API Key.

### 1. Configure Environment Variables
1. Locate the `.env.example` file in the root directory.
2. Rename it to `.env`.
3. Open `.env` and paste your actual OpenAI API Key:
   ```env
   OPENAI_API_KEY=sk-your-real-key-here
   ```

### 2. Start the Application
Run the following command in your terminal at the project root:
```bash
docker-compose up --build
```
*Note: The API runs on port `8000`. The PostgreSQL database runs on port `5432`.*

---

## 📚 API Documentation

Once the application is running, the auto-generated interactive documentation is available at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🧪 How to Run the Tests

The test suite uses `pytest` and mocks the database and OpenAI calls to ensure isolated, fast, and deterministic testing. 

You can run the full test suite directly inside the Docker container:
```bash
docker-compose exec api pytest
```
*(Ensure the application is running via `docker-compose up` before executing this command).*

---

## 🧠 Design Decisions & Assumptions

### 1. Multi-Tenant Architecture
- **Decision:** Strict logical isolation at the database layer. Every API endpoint requires an `x-tenant-id` UUID header.
- **Assumption:** Customers operate in highly isolated silos. The `Asset` and `AssetRelationship` tables use `tenant_id` as a strict foreign key and a composite unique constraint (`tenant_id`, `type`, `value`) to prevent cross-tenant collisions.

### 2. Idempotent Ingestion Strategy
- **Decision:** The `/import` endpoint uses a PostgreSQL `ON CONFLICT DO UPDATE` (upsert) strategy.
- **Assumption:** Scanners will blindly push duplicate data repeatedly. The API must gracefully handle this without creating duplicates or throwing errors, updating only the `last_seen` timestamp and merging tags.

### 3. LLM Cost Optimization (Caching)
- **Decision:** AI Enrichment and Risk Scoring results are aggressively cached in memory (simulated via Python dictionaries for the PoC, ready for Redis).
- **Assumption:** LLM calls are expensive and slow. If a scanner uploads the exact same IP address 50 times, the LLM is only called once.

### 4. Deterministic AI Outputs
- **Decision:** LangChain and Pydantic `with_structured_output` are used to mathematically force the LLM to return strict JSON structures (e.g., `{ "score": 85, "reason": "..." }`).
- **Assumption:** The AI must act as a reliable microservice. Free-text LLM hallucinations would break the database schema.

---

## 🤖 AI Track: Example Prompts & Outputs

### Capability 1: Natural Language Querying
**Prompt:**
> *"List all my internal production databases and their IP addresses."*

**AI Output (JSON):**
```json
{
  "response": "Here are your internal production databases:\n- 192.168.1.50 (Tags: database, prod, internal)\n- 10.0.0.15 (Tags: database, internal)"
}
```

### Capability 2: Automated Risk Scoring
**System Prompt:**
> *"You are a Cybersecurity Risk Assessor. Calculate a risk score (0-100) based on the asset's type, value, and tags. Return strictly JSON."*

**AI Output (Structured JSON):**
```json
{
  "score": 85,
  "reason": "The asset '192.168.1.50' is tagged as a 'database' but lacks 'internal' tags, suggesting it might be exposed to the internet, which is a critical risk."
}
```

### Capability 3: Automated Enrichment
**System Prompt:**
> *"Categorize this asset based on its type and value. Return the category and a confidence percentage."*

**AI Output (Structured JSON):**
```json
{
  "category": "Cloud Infrastructure",
  "confidence": 95,
  "rationale": "The domain 's3-bucket-company.amazonaws.com' is a well-known AWS storage bucket format."
}
```

### Capability 4: Executive Report Generation
**System Prompt:**
> *"You are a CISO. Write a markdown Executive Summary analyzing these assets..."*

**AI Output (Markdown):**
```markdown
# Executive Cybersecurity Summary
## Overview
We have ingested 14 internet-facing assets. 
## Critical Findings
- 2 Databases are currently missing internal security tags.
- The average risk score across the fleet is 45/100.
## Recommendations
Immediate review of IP segment 192.168.x.x is required.
```
