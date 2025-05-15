import cv2 as cv
from PIL import Image
import numpy as np

# define a function to preprocessing
# include grayscale, median filter, OTSU threshold
# def preprocess_image(pil_img: Image.Image) ->Image.Image:
#     # PIL to np.array
#     img = np.array(pil_img)
    
#     # grayscale
#     gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    
#     # apply median filter
#     denoised = cv.medianBlur(gray, 3)
#     denoised = cv.normalize(denoised, None, 0, 255, cv.NORM_MINMAX)
    
#     # Threshold
#     _, binary = cv.threshold(denoised,0, 255, cv.THRESH_BINARY+cv.THRESH_OTSU)
    
#     # np.array to PIL and transfer back to RGB
#     preprocessed_img = Image.fromarray(cv.cvtColor(binary,cv.COLOR_GRAY2RGB))
#     return preprocessed_img

# Lightweight preprocessing: just grayscale and convert back to RGB

# Just for quicker testing uncomment after
def preprocess_image(pil_img: Image.Image) -> Image.Image:
    gray = pil_img.convert("L")
    return gray.convert("RGB")

    
    