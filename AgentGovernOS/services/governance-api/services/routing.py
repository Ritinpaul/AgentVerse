from typing import Any


class RoutingService:
    @staticmethod
    def recommend_model(prompt: str, current_model: str) -> dict[str, Any]:
        """
        Analyzes prompt complexity to recommend a cheaper/faster model.
        In production, this could use Semantic Router, Embeddings, or Heuristics.
        We use simple heuristics to demonstrate the routing logic.
        """
        # If the user is already using a cheap model, leave it alone.
        cheap_models = ["llama3-8b", "gpt-3.5-turbo", "claude-3-haiku"]
        if current_model.lower in cheap_models:
            return {"action": "continue", "recommended_model": current_model}

        word_count = len(prompt.split)
        
        # Simple heuristic: If it's a short query with simple intent, route to a cheaper model
        if word_count < 20 and "complex" not in prompt.lower and "analyze" not in prompt.lower:
            # Suggest a fallback to save cost
            return {
                "action": "fallback", 
                "recommended_model": "claude-3-haiku",
                "reason": "Task complexity is low. Routing to cheaper model to optimize cost."
            }
            
        return {"action": "continue", "recommended_model": current_model}
