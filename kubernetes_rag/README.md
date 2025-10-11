# Kubernetes RAG System

A comprehensive Retrieval-Augmented Generation (RAG) system for Kubernetes learning and testing. This system intelligently processes Kubernetes documentation, stores it in a vector database, and provides accurate answers to Kubernetes-related questions using LLM technology.

## Features

- **Intelligent Document Processing**: Processes markdown documentation with smart chunking
- **Q&A Extraction**: Automatically extracts question-answer pairs from documentation
- **Semantic Search**: Uses sentence transformers for semantic similarity search
- **Re-ranking**: Cross-encoder re-ranking for improved retrieval accuracy
- **LLM Integration**: Supports OpenAI, Anthropic, and local models
- **Dual Interface**: Both CLI and REST API available
- **Flexible Configuration**: Easy-to-customize YAML configuration
- **Vector Storage**: ChromaDB for efficient embedding storage and retrieval

## Architecture

```
┌─────────────┐
│   User      │
└─────┬───────┘
      │
      ├─── CLI ────────┐
      │                │
      └─── REST API ───┤
                       │
              ┌────────▼────────┐
              │   RAG System    │
              ├─────────────────┤
              │  Query Engine   │
              └────────┬────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │Retriever│   │Embedder │   │Generator│
   └────┬────┘   └────┬────┘   └────┬────┘
        │             │              │
   ┌────▼────────────▼────┐    ┌────▼────┐
   │   Vector Database    │    │   LLM   │
   │     (ChromaDB)       │    │(OpenAI) │
   └──────────────────────┘    └─────────┘
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) CUDA for GPU acceleration

### Setup

1. **Clone the repository**:

```bash
cd kubernetes_rag
```

2. **Create a virtual environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
OPENAI_API_KEY=your_openai_api_key_here
# or
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

5. **Install the package**:

```bash
pip install -e .
```

## Quick Start

### 1. Ingest Documentation

First, save the Kubernetes documentation to a file and ingest it:

```bash
# Ingest a single file
python -m src.cli ingest path/to/kubernetes_doc.md

# Ingest a directory
python -m src.cli ingest path/to/docs/ --file-pattern "*.md"
```

### 2. Query the System

**Using CLI**:

```bash
# Simple query
python -m src.cli query "What is a Pod in Kubernetes?"

# Search without generating answer
python -m src.cli search "Kubernetes deployment" --top-k 3

# Interactive mode
python -m src.cli interactive
```

**Using REST API**:

First, start the API server:

```bash
python -m src.api
```

Then query via HTTP:

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is a Pod in Kubernetes?",
    "top_k": 5,
    "generate_answer": true
  }'
```

## Configuration

The system is configured via `config/config.yaml`:

```yaml
# Embedding Model
embedding:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  embedding_dim: 384
  batch_size: 32

# Vector Database
vector_db:
  type: "chromadb"
  persist_directory: "./data/vector_db"
  collection_name: "kubernetes_docs"

# LLM Configuration
llm:
  provider: "openai" # Options: openai, anthropic, local
  model_name: "gpt-3.5-turbo"
  temperature: 0.3
  max_tokens: 1000

# Retrieval Settings
retrieval:
  top_k: 5
  score_threshold: 0.7
  rerank: true
  rerank_top_k: 3
```

## CLI Commands

### Ingestion

```bash
# Ingest documents
python -m src.cli ingest <source> [--file-pattern PATTERN]

# Example
python -m src.cli ingest ./kubernetes_docs --file-pattern "*.md"
```

### Querying

```bash
# Query with answer generation
python -m src.cli query "Your question here"

# Search only (no answer generation)
python -m src.cli search "Your search query" --top-k 5

# Filter by category
python -m src.cli search "deployment" --category qa_pair
```

### Interactive Mode

```bash
python -m src.cli interactive
```

### System Management

```bash
# View statistics
python -m src.cli stats

# Reset database
python -m src.cli reset --yes
```

## API Endpoints

### Query Endpoint

```http
POST /query
Content-Type: application/json

{
  "query": "What is a Kubernetes Pod?",
  "top_k": 5,
  "generate_answer": true,
  "temperature": 0.3
}
```

### Search Endpoint

```http
POST /search
Content-Type: application/json

{
  "query": "kubernetes deployment",
  "top_k": 5,
  "category": "qa_pair",
  "score_threshold": 0.7
}
```

### Ingest Endpoint

```http
POST /ingest
Content-Type: application/json

{
  "text": "Your text content here",
  "metadata": {"source": "custom"},
  "source_name": "my_document"
}
```

### Stats Endpoint

```http
GET /stats
```

## Usage Examples

### Python API

```python
from src.utils.config_loader import get_config
from src.ingestion.pipeline import create_ingestion_pipeline
from src.retrieval.retriever import create_retriever
from src.generation.llm import create_rag_generator

# Load configuration
config, settings = get_config()

# Create components
pipeline = create_ingestion_pipeline(config)
retriever = create_retriever(config)
generator = create_rag_generator(config)

# Ingest documents
pipeline.ingest_directory("./docs")

# Query
query = "What is a Kubernetes Service?"
results = retriever.retrieve(query, top_k=5)

# Generate answer
answer = generator.generate_answer(query, results)
print(answer['answer'])
```

### Programmatic Ingestion

```python
from pathlib import Path
from src.ingestion.pipeline import create_ingestion_pipeline
from src.utils.config_loader import get_config

config, _ = get_config()
pipeline = create_ingestion_pipeline(config)

# Ingest text directly
pipeline.ingest_from_text(
    text="Kubernetes is a container orchestration platform...",
    metadata={"source": "manual", "topic": "intro"},
    source_name="k8s_intro"
)

# Ingest file
pipeline.ingest_file(Path("./kubernetes_basics.md"))

# Ingest directory
stats = pipeline.ingest_directory(Path("./docs"))
print(f"Ingested {stats['total_chunks']} chunks from {stats['processed_files']} files")
```

## Advanced Features

### Custom Retrieval

```python
from src.retrieval.retriever import Retriever

# Multi-query retrieval
queries = [
    "What is a Pod?",
    "Explain Kubernetes Pod",
    "Pod definition in K8s"
]

results = retriever.multi_query_retrieve(
    queries,
    top_k=5,
    merge_strategy="unique"
)

# Category-based retrieval
qa_results = retriever.retrieve_by_category(
    query="What is a deployment?",
    category="qa_pair",
    top_k=3
)
```

### Conversational RAG

```python
conversation_history = []

while True:
    query = input("You: ")
    if query.lower() == 'exit':
        break

    results = retriever.retrieve(query, top_k=5)

    answer_data = generator.generate_with_followup(
        query,
        results,
        conversation_history
    )

    conversation_history = answer_data['conversation_history']
    print(f"Assistant: {answer_data['answer']}")
```

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_document_processor.py -v
```

## Project Structure

```
kubernetes_rag/
├── config/
│   └── config.yaml           # System configuration
├── data/
│   ├── raw/                  # Raw documentation files
│   ├── processed/            # Processed documents
│   └── vector_db/            # ChromaDB storage
├── src/
│   ├── ingestion/
│   │   ├── document_processor.py
│   │   ├── embeddings.py
│   │   └── pipeline.py
│   ├── retrieval/
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── generation/
│   │   └── llm.py
│   ├── utils/
│   │   ├── config_loader.py
│   │   └── logger.py
│   ├── cli.py               # CLI interface
│   └── api.py               # REST API
├── tests/
│   ├── test_document_processor.py
│   └── test_retriever.py
├── requirements.txt
├── setup.py
└── README.md
```

## Performance Tips

1. **GPU Acceleration**: Install PyTorch with CUDA support for faster embedding generation
2. **Batch Size**: Adjust `embedding.batch_size` in config for optimal performance
3. **Chunk Size**: Experiment with `document_processing.chunk_size` for your use case
4. **Re-ranking**: Disable re-ranking for faster retrieval if accuracy is sufficient

## Troubleshooting

### Issue: API key not found

- Ensure `.env` file exists and contains valid API keys
- Check environment variables are loaded correctly

### Issue: Slow embedding generation

- Reduce batch size in config
- Consider using a smaller embedding model
- Enable GPU acceleration if available

### Issue: Poor retrieval quality

- Increase `top_k` value
- Enable re-ranking in config
- Adjust `chunk_size` and `chunk_overlap`
- Lower `score_threshold` to get more results

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with LangChain, ChromaDB, and Sentence Transformers
- Kubernetes documentation from kubernetes.io
- OpenAI/Anthropic for LLM capabilities

## Contact

For questions or support, please open an issue on GitHub.

---

**Happy Kubernetes Learning! 🚀**
