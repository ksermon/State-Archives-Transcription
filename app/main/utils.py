import fitz
import os
import io
from flask import flash, redirect, url_for, render_template
from base64 import b64encode

def pdf_to_images_base64(pdf_bytes):
    # read pdf_bytes from database
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images_base64 = []

    for pg in range(doc.page_count):
        page = doc.load_page(pg)
        zoom = 2 #The larger the zoom factor, the clearer the image will be.
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # convert pdf into png
        img_bytes = pix.tobytes(output="png")

        # use base64 code to store
        img_base64 = b64encode(img_bytes).decode("utf-8")
        images_base64.append(img_base64)

    return images_base64