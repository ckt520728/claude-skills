"""kgengine — LLM-built knowledge graphs over a personal research library.

Pipeline (after anthropics/claude-cookbooks capabilities/knowledge_graph):
ingest -> extract (NER+RE, structured outputs) -> resolve (entity resolution) -> summarize -> query/visualize.
Model-agnostic: Claude (CLI login or API), Ollama, any OpenAI-compatible endpoint.
"""
__version__ = "0.1.0"
