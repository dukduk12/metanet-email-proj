from wordcloud import WordCloud
import matplotlib.pyplot as plt
from pathlib import Path
from loguru import logger
from src.config import settings
import os

def generate_word_cloud(text: str, output_filename: str = "wordcloud.png") -> Path:
    """
    Generates a word cloud from the given text and saves it as an image.
    """
    logger.info(f"Generating word cloud for {output_filename}")
    
    # Windows default Korean font path
    font_path = "C:/Windows/Fonts/malgun.ttf"
    if not os.path.exists(font_path):
        logger.warning(f"Font not found at {font_path}, fallback to default.")
        font_path = None
        
    try:
        wc = WordCloud(
            font_path=font_path,
            width=800,
            height=400,
            background_color='white',
            max_words=100
        ).generate(text)
        
        output_path = settings.output_dir / output_filename
        
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.savefig(output_path)
        plt.close()
        
        logger.info(f"Word cloud saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating word cloud: {e}")
        return None
