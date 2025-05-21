from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
from .preprocessing import preprocess_image

# Trying to optimize the model loading

MODEL_PATH = "microsoft/trocr-base-handwritten"

def load_model():
    
    # Allow for GPU usage if available
    # device = torch.device('cuda:0' if torch.cuda.is_available else 'cpu')
    # global processor, model
    # if processor is None or model is None:
    processor = TrOCRProcessor.from_pretrained(MODEL_PATH)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH)
    # print("This is the processor: "+ processor + " and model: " + model)
    model.eval()
    return processor, model

def recognize_single_image(img: Image.Image, processor, model) -> str:
    # load_model()  
    # apply preprocessing
    # img = preprocess_image(img)
    
    # with torch.no_grad():
    #     pixel_values = processor(images=img, return_tensors="pt").pixel_values
    #     generated_ids = model.generate(pixel_values)
    #     text = processor.batch_decode(generated_ids, skip_special_tokens = True)[0]
    #     return text.strip()
    
    with torch.no_grad():
        pixel_values = processor(images=img, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text.strip()

def recognize_batch_images(images: list[Image.Image], processor, model) -> list[str]:
    with torch.no_grad():
        pixel_values = processor(images=images, return_tensors="pt", padding=True).pixel_values
        generated_ids = model.generate(pixel_values)
        return processor.batch_decode(generated_ids, skip_special_tokens=True)
