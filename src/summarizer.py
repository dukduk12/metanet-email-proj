from google import genai
from loguru import logger
from src.config import settings

def summarize_text(text: str) -> str:
    """
    Summarizes the given text using Gemini API.
    """
    if not text.strip():
        return "No text to summarize."
        
    logger.info("Summarizing text with Gemini API")
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        
        prompt = f"""
        다음 텍스트를 핵심 내용 위주로 요약해줘:
        
        {text}
        """
        
        # gemini-2.5-flash is a good default fast model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        logger.info("Summarization complete.")
        return response.text
    except Exception as e:
        logger.error(f"Error during summarization: {e}")
        return f"요약 중 오류가 발생했습니다: {e}"
