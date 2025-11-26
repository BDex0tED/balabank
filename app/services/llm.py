from google import genai

client = genai.Client(api_key="AIzaSyCqv5LRxlTDb12eFlWua3iBFBlpmY0QF74") # <- укажи здесь свой api_key

def ask_llm(prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    return response.text
