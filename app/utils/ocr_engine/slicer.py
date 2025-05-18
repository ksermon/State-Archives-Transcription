import cv2 as cv
import numpy as np 
from typing import List
from PIL import Image


def auto_slice_lines(pil_imgae: Image.Image, min_height: int = 10, padding: int =10)->List[Image.Image]:
    # convert OpenCv format
    image = np.array(pil_imgae.convert("RGB"))
    gray = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
    
    # Preprocessing
    blurred = cv.medianBlur(gray, 3)
    _, thresh = cv.threshold(blurred, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    
    # Canny
    edges = cv.Canny(thresh, 30, 100)
    edges = cv.bitwise_not(edges)
    kernel = cv.getStructuringElement(cv.MORPH_RECT, (60,3))
    dilated = cv.morphologyEx(edges, cv.MORPH_OPEN ,kernel, iterations=2)
    dilated = cv.dilate(dilated, kernel,iterations=2)
    dilated = cv.bitwise_not(dilated)
    
    # find contours
    contours, _ = cv.findContours(dilated, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    
    valid_contours = []
    for cnt in contours:
        x, y, w, h = cv.boundingRect(cnt)
        area = cv.contourArea(cnt)
        if 50< area < 0.9 * thresh.shape[0] * thresh.shape[1]:  
            valid_contours.append(cnt)
        
    lines = []
    for cnt in valid_contours:
        x, y, w, h = cv.boundingRect(cnt)
        if h > min_height:
            top = max(0, y-padding)
            bottom = min(image.shape[0], y+h+padding)
            lines.append((top,bottom))
    

    lines.sort(key=lambda b: b[0])
    target_height = 64 

    cropped_lines = []
    for idx, (top, bottom) in enumerate(lines):
        cropped = pil_imgae.crop((0, top, pil_imgae.width, bottom))
        
        # Resize
        w, h = cropped.size
        scale_ratio = target_height / h
        new_width = int(w * scale_ratio)
        resized = cropped.resize((new_width, target_height), Image.LANCZOS)
        
        cropped_lines.append(resized)

    return cropped_lines    
                
    