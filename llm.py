import time
from typing import List, Union
from openai import OpenAI

class LLMClient:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def ask(self, questions: Union[str, List[str]], context: str = "") -> Union[str, List[str]]:
        """
        Ask the LLM one or multiple questions with shared context.
        - If `questions` is a string, returns a single string.
        - If `questions` is a list, returns a list of strings.
        """
        # Ensure questions is a list
        is_single = isinstance(questions, str)
        if is_single:
            questions = [questions]

        # Build the prompt
        q_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        user_prompt = f"Answer the following questions based on the context.\n\nContext:\n{context}\n\nQuestions:\n{q_text}\n\nReturn answers as a JSON list of strings."

        # Retry logic
        retries = 3
        for i in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful teaching assistant."},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                )
                content = response.choices[0].message.content.strip()

                # If multiple questions, expect JSON list back
                if not is_single:
                    import json
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # fallback: split by newline
                        return [line.strip("-• ") for line in content.splitlines() if line.strip()]
                return content

            except Exception as e:
                if "rate_limit_exceeded" in str(e) and i < retries - 1:
                    wait_time = (i + 1) * 5
                    print(f"⚠️ Rate limit hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return f"LLM error: {str(e)}"
