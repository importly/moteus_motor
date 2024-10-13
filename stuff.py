import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import os

# File paths
input_pdf = "C:/Users/aryan/Downloads/processed/pages.pdf"
output_pdf = 'C:/Users/aryan/Downloads/processed/pages2.pdf'

# Temporary folder to store the processed images
temp_folder = 'temp_images'
if not os.path.exists(temp_folder):
	os.makedirs(temp_folder)

# Open the PDF
doc = fitz.open(input_pdf)

# Loop through each page
for i in range(len(doc)):
	# Extract the page as a pixmap (image)
	page = doc.load_page(i)
	pix = page.get_pixmap()

	# Convert pixmap to numpy array for OpenCV
	img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

	if pix.n > 1:  # Convert to grayscale if it's not already
		img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

	# Apply adaptive thresholding to avoid over-darkening
	thresh_img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

	# Save the processed image as a temporary file
	temp_img_path = os.path.join(temp_folder, f'page_{i + 1}.png')
	cv2.imwrite(temp_img_path, thresh_img)

# Convert all the processed images back into a PDF
image_list = []
for i in range(len(doc)):
	temp_img_path = os.path.join(temp_folder, f'page_{i + 1}.png')
	img = Image.open(temp_img_path).convert('RGB')
	image_list.append(img)

# Save as a single PDF
image_list[0].save(output_pdf, save_all=True, append_images=image_list[1:])

# Clean up temporary files
for i in range(len(doc)):
	os.remove(os.path.join(temp_folder, f'page_{i + 1}.png'))

print("PDF processing complete!")