from google import genai

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None # <- укажи здесь свой api_key

def ask_llm(prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    return response.text
