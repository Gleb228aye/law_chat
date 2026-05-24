from app.config import settings


class LLMConfigurationError(RuntimeError):
    pass


class LLMClient:
    def __init__(self) -> None:
        if not settings.llm_api_key:
            raise LLMConfigurationError("LLM is not configured")

        from openai import OpenAI

        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    def generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.llm_model_name,
            temperature=settings.llm_temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        message = response.choices[0].message
        return (message.content or "").strip()
