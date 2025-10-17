import os
import base64
import io
from PIL import Image
import google.generativeai as genai

# Configure the Gemini API key from environment variables
try:
    if api_key := os.environ.get("GOOGLE_AI_API_KEY"):
        genai.configure(api_key=api_key)
    else:
        print("WARNING: GOOGLE_AI_API_KEY environment variable not set.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

def transcribe_images_with_gemini(image_batch_base64,mark_uncertainty: bool = True) -> list[str]:
    """
    Transcribes a batch of images using the Gemini 1.5 Pro model.

    Args:
        image_batch_base64: A list of base64-encoded image strings.
        mark_uncertainty: Whether to apply uncertainty marking rules.

    Returns:
        A list of transcriptions, one for each image in the batch.
    """
    if not os.environ.get("GOOGLE_AI_API_KEY"):
        raise ValueError("Gemini API key is not configured. Cannot proceed.")
        
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    pil_images = [Image.open(io.BytesIO(base64.b64decode(b64_str))) for b64_str in image_batch_base64]



    prompt_parts = [
        "Transcribe the text from the following images of handwritten documents.",
        "Output only the direct transcription for each page.",
        "Separate the transcription of each page with the exact delimiter '---PAGE BREAK---'.",
        "If a page is blank, output only the delimiter for that page."
    ]

# rules mark uncertain characters
    if mark_uncertainty:
        rules_prompt = """
## Identifying and Marking Uncertain Items:
* For the following situations, **bold** marking must be used:
    - Characters with unclear outlines due to messy handwriting
    - Characters with broken strokes or interference from stains/smudges
    - Instances where similar characters are difficult to distinguish 
    - Recognition results with a confidence score below 85% (self-estimate)
* For sequences of 3 or more consecutive low-confidence characters, **bold the entire sequence**.
* For handwritten text, apply a more lenient marking strategy: **bold** any character with blurred or ambiguous strokes.
"""
        prompt_parts.insert(2, "Apply the following uncertainty marking rules:")
        prompt_parts.insert(3, rules_prompt)


    prompt_parts.extend(pil_images)

    try:
        response = model.generate_content(prompt_parts)
        transcriptions = response.text.split('---PAGE BREAK---')
        
        # Ensure the output list matches the input batch size
        cleaned_transcriptions = [t.strip() for t in transcriptions]
        if len(cleaned_transcriptions) > len(pil_images):
            cleaned_transcriptions = cleaned_transcriptions[:len(pil_images)]
        while len(cleaned_transcriptions) < len(pil_images):
            cleaned_transcriptions.append("[Transcription failed for this page]")
            
        return cleaned_transcriptions

    except Exception as e:
        print(f"An error occurred during the Gemini API call: {e}")
        return [f"[Transcription Failed: {e}]"] * len(image_batch_base64)