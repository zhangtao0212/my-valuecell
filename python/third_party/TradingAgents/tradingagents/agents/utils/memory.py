import os
import chromadb
from chromadb.config import Settings
from openai import OpenAI


class FinancialSituationMemory:
    def __init__(self, name, config):
        self.embedding = config["EMBEDDER_MODEL_ID"]
        self.client = OpenAI(base_url=config["EMBEDDER_BASE_URL"])
        if "localhost" not in config["EMBEDDER_BASE_URL"]:
            EMBEDDER_API_KEY = os.getenv("EMBEDDER_API_KEY") or os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=EMBEDDER_API_KEY, base_url=config["EMBEDDER_BASE_URL"])

        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        try:
            self.situation_collection = self.chroma_client.create_collection(name=name)
        except Exception as e:
            if "already exists" in str(e):
                print(f"💾 Collection '{name}' already exists, using existing collection")
                self.situation_collection = self.chroma_client.get_collection(name=name)
            else:
                raise e

    def get_embedding(self, text):
        """Get OpenAI embedding for a text"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding
        except Exception as e:
            # If the current client fails (e.g., OpenRouter doesn't support embeddings),
            # try alternative approaches
            print(f"⚠️  Embedding request failed with current provider: {str(e)}")
            
            # Return a dummy embedding vector of the expected dimension (1536 for text-embedding-3-small)
            print("Using dummy embeddings as fallback...")
            import random
            return [random.random() for _ in range(1536)]

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using OpenAI embeddings"""
        query_embedding = self.get_embedding(current_situation)

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": results["metadatas"][0][i]["recommendation"],
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
