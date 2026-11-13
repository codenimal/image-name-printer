import io
import os
import zipfile
import openpyxl
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Print-Nimal")
st.title("Print-Nimal")

club_selection = st.selectbox("Select Club", ["cd", "green", "logic", "theater"])
uploaded_excel = st.file_uploader("Upload Excel File", type=["xlsx"])
uploaded_image = st.file_uploader("Upload Image Template", type=["png", "jpg", "jpeg"])

def get_system_font(font_size=35):
    font_paths = [
        "times.ttf",
        r"C:\Windows\Fonts\times.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=font_size)
            except Exception:
                continue
    return ImageFont.load_default()

def detect_certificate_underline(pil_image):
    gray_img = pil_image.convert("L")
    width, height = gray_img.size
    longest_line_length = 0
    best_line_x_start = 0
    best_line_x_end = 0
    best_line_y = 0
    
    start_y = int(height * 0.30)
    end_y = int(height * 0.75)
    
    for y in range(start_y, end_y):
        current_line_length = 0
        current_start_x = None
        for x in range(0, width):
            pixel_value = gray_img.getpixel((x, y))
            if pixel_value < 80:  
                if current_start_x is None:
                    current_start_x = x
                current_line_length += 1
            else:
                if current_start_x is not None:
                    if current_line_length > longest_line_length:
                        longest_line_length = current_line_length
                        best_line_x_start = current_start_x
                        best_line_x_end = x
                        best_line_y = y
                    current_line_length = 0
                    current_start_x = None
        if current_start_x is not None:
            if current_line_length > longest_line_length:
                longest_line_length = current_line_length
                best_line_x_start = current_start_x
                best_line_x_end = width
                best_line_y = y
                
    if longest_line_length < (width * 0.2):
        return int(width * 0.25), int(width * 0.75), int(height * 0.55)
    return best_line_x_start, best_line_x_end, best_line_y

if st.button("Generate Images"):
    if not uploaded_excel or not uploaded_image:
        st.error("Please upload both the Excel file and the image template.")
    else:
        with st.spinner("Processing certificates... Please wait."):
            
            wb = openpyxl.load_workbook(uploaded_excel, data_only=True)
            sheet = wb.active
            
            with Image.open(uploaded_image) as loaded_img:
                base_image = loaded_img.convert("RGB")
                img_width, img_height = base_image.size
                
                
                line_start_x, line_end_x, line_y = detect_certificate_underline(base_image)
                available_width = line_end_x - line_start_x
                
                
                base_font_size = 35 if 35 > int(img_width * 0.04) else int(img_width * 0.04)
                generated_files = {}
                success_count = 0
                
                
                for row in sheet.iter_rows(min_row=1, max_col=1, values_only=True):
                    
                    if row and isinstance(row, (tuple, list)):
                        cell_value = row[0]
                    else:
                        cell_value = row
                        
                    if cell_value is None:
                        continue
                        
                    name = str(cell_value).strip()
                    if not name or name.lower() == "none":
                        continue
                        
                    image_copy = base_image.copy()
                    draw_canvas = ImageDraw.Draw(image_copy)
                    
                   
                    current_font_size = base_font_size
                    font = get_system_font(font_size=current_font_size)
                    text_width = draw_canvas.textlength(name, font=font)
                    
                    while text_width > (available_width * 0.95) and current_font_size > 14:
                        current_font_size -= 2
                        font = get_system_font(font_size=current_font_size)
                        text_width = draw_canvas.textlength(name, font=font)
                        
                    
                    target_y = line_y - int(current_font_size * 1.15)
                    target_x = line_start_x + (available_width - text_width) / 2
                    
                    
                    draw_canvas.text(
                        (target_x, target_y), name, fill=(17, 30, 56), font=font
                    )
                    
                    
                    clean_filename = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
                    output_filename = f"{clean_filename}.png"
                    
                    
                    buf = io.BytesIO()
                    image_copy.save(buf, format="PNG")
                    generated_files[output_filename] = buf.getvalue()
                    success_count += 1
                    
                if success_count > 0:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for file_name, file_data in generated_files.items():
                            zip_file.writestr(file_name, file_data)
                            
                    st.success(f"Successfully processed {success_count} names for {club_selection}!")
                    st.download_button(
                        label="Download All Generated Images (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"{club_selection}_generated_images.zip",
                        mime="application/zip",
                    )
                else:
                    st.error("No names could be read or extracted from the uploaded Excel column.")
