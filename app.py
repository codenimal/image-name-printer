import os
import warnings
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont
import openpyxl
import streamlit as st

warnings.filterwarnings("ignore")


st.title("print-nimal")
club_selection = st.selectbox("select club", ["cd", "green", "logic", "therter"])
uploaded_excel = st.file_uploader("upload excel file", type=["xlsx"])
uploaded_image = st.file_uploader("upload image template", type=["png", "jpg", "jpeg"])

def get_system_font(font_size=20):
    
    font_paths = [
        r"C:\Windows\Fonts\times.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
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
                    
        if current_start_x is not None and current_line_length > longest_line_length:
            longest_line_length = current_line_length
            best_line_x_start = current_start_x
            best_line_x_end = width
            best_line_y = y

    if longest_line_length < (width * 0.2):
        return int(width * 0.25), int(width * 0.75), int(height * 0.55)
    return best_line_x_start, best_line_x_end, best_line_y

if st.button("generate images"):
    if not uploaded_excel or not uploaded_image:
        st.error("please upload both the excel file and the image template.")
    else:
        st.info("please wait...")
        
        wb = openpyxl.load_workbook(uploaded_excel)
        sheet = wb.active
        base_image = Image.open(uploaded_image).convert("RGB")
        img_width, img_height = base_image.size
        
        line_start_x, line_end_x, line_y = detect_certificate_underline(base_image)
        available_width = line_end_x - line_start_x
        calculated_font_size = int(img_width * 0.04) 
        font = get_system_font(font_size=calculated_font_size)
        target_y = line_y - int(calculated_font_size * 1.1)
        
        generated_files = {}
        success_count = 0
        
        for row in sheet.iter_rows(min_row=1, max_col=1, values_only=True):
            if not row:
                continue
            
            cell_value = row[0]
            if cell_value is None:
                continue
                
            name = str(cell_value).strip()
            if not name or name.lower() == "none":
                continue
                
            imageopen = base_image.copy()
            draw = ImageDraw.Draw(imageopen)
            
            text_width = draw.textlength(name, font=font)
            target_x = line_start_x + (available_width - text_width) / 2
            
            draw.text((target_x, target_y), name, fill=(17, 30, 56), font=font)
            
            clean_filename = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
            output_filename = f"{clean_filename}.png"
            
            buf = io.bytesio()
            imageopen.save(buf, format="PNG")
            generated_files[output_filename] = buf.getvalue()
            success_count += 1
            
        if success_count > 0:
            zip_buffer = io.bytesio()
            with zipfile.zipfile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_name, file_data in generated_files.items():
                    zip_file.writestr(file_name, file_data)
                    
            st.success(f"successfully processed {success_count} names for {club_selection}!")
            st.download_button(
                label="download all generated images (zip)",
                data=zip_buffer.getvalue(),
                file_name=f"{club_selection}_generated_images.zip",
                mime="application/zip"
            )
        else:
            st.error("no names could be read or extracted from the uploaded excel column.")
