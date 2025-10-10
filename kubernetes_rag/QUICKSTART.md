# Quick Start Guide - Kubernetes RAG System

This guide will help you get started with the Kubernetes RAG system in under 5 minutes.

## Step 1: Installation (2 minutes)

```bash
# Navigate to project directory
cd kubernetes_rag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

## Step 2: Configuration (1 minute)

Create `.env` file:

```bash
# Copy example
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

Or use environment variable:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

## Step 3: Ingest Documentation (1 minute)

Save your Kubernetes documentation to a file (e.g., `kubernetes_doc.md`) or use the provided sample:

```bash
# Ingest the Kubernetes documentation you provided
python -m src.cli ingest ../README.md
```

Or create a test document:

```python
# save_test_doc.py
content = """
# Kubernetes Basics

<details>
<summary>What is a Pod?</summary><br><b>
A Pod is the smallest deployable unit in Kubernetes. It can contain one or more containers.
</b></details>

<details>
<summary>What is a Service?</summary><br><b>
A Service is an abstract way to expose an application running on Pods as a network service.
</b></details>
"""

with open('k8s_basics.md', 'w') as f:
    f.write(content)
```

Then ingest:
```bash
python -m src.cli ingest k8s_basics.md
```

## Step 4: Query the System (30 seconds)

### Option A: CLI

```bash
# Ask a question
python -m src.cli query "What is a Pod in Kubernetes?"

# Interactive mode
python -m src.cli interactive
```

### Option B: REST API

Terminal 1 - Start server:
```bash
python -m src.api
```

Terminal 2 - Query:
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is a Pod in Kubernetes?",
    "top_k": 5
  }'
```

## Step 5: Explore Features

### Search without generating answer
```bash
python -m src.cli search "kubernetes service" --top-k 3
```

### Filter by category
```bash
python -m src.cli search "pod" --category qa_pair
```

### View statistics
```bash
python -m src.cli stats
```

## Python API Usage

```python
from src.utils.config_loader import get_config
from src.retrieval.retriever import create_retriever
from src.generation.llm import create_rag_generator

# Load config
config, _ = get_config()

# Create components
retriever = create_retriever(config)
generator = create_rag_generator(config)

# Query
query = "What is a Kubernetes Deployment?"
results = retriever.retrieve(query, top_k=5)

# Generate answer
answer = generator.generate_answer(query, results)
print(answer['answer'])
```

## Common Commands Cheat Sheet

```bash
# Ingestion
python -m src.cli ingest <file_or_directory>
python -m src.cli ingest ./docs --file-pattern "*.md"

# Querying
python -m src.cli query "your question"
python -m src.cli search "search term" --top-k 5
python -m src.cli interactive

# Management
python -m src.cli stats
python -m src.cli reset --yes

# API
python -m src.api  # Start server on localhost:8000
```

## API Endpoints

- `POST /query` - Query with answer generation
- `POST /search` - Search documents only
- `POST /ingest` - Ingest text directly
- `GET /stats` - System statistics
- `GET /health` - Health check

## Next Steps

1. **Customize Configuration**: Edit `config/config.yaml` to adjust:
   - Embedding model
   - LLM provider and model
   - Retrieval parameters
   - Chunk size and overlap

2. **Ingest More Documents**: Add your Kubernetes documentation, exercises, or Q&A

3. **Explore Advanced Features**:
   - Multi-query retrieval
   - Conversational mode
   - Custom metadata filtering
   - Re-ranking configuration

4. **Integration**: Integrate the API into your application or build a custom UI

## Troubleshooting

**Q: "No module named 'src'"**
- Run `pip install -e .` from the kubernetes_rag directory

**Q: "OpenAI API key not found"**
- Ensure `.env` file exists with `OPENAI_API_KEY=your-key`
- Or set environment variable: `export OPENAI_API_KEY=your-key`

**Q: "No results found"**
- Make sure you've ingested documents first
- Try lowering the score_threshold in config
- Increase top_k value

**Q: API server won't start**
- Check if port 8000 is already in use
- Try different port in config/config.yaml

## Support

For issues, questions, or contributions:
- Check the full README.md
- Review the code documentation
- Open an issue on GitHub

Happy Learning! 🚀
