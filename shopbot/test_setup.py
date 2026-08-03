# test_setup.py
# Source: Book 1, Chapter 2
# Run this before building anything else. 1536 means the foundation holds.

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embeddings = OpenAIEmbeddings()

result = embeddings.embed_query("Does this kurta come in size S?")

print("Setup working.")
print(f"API key found: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"Embedding dimensions: {len(result)}")
print(f"First three values: {result[:3]}")
