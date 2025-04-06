import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class OpenAIBackend:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=api_key)
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def generate_response(
        self, prompt, model=None, system_prompt="You are a helpful assistant."
    ):

        if model is None:
            model = self.default_model

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8000,
                temperature=0.7,
                timeout=120,  
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    def get_available_models(self):

        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            return f"Error retrieving models: {str(e)}"
