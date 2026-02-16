import csv
import os
from PIL import Image
import piexif
from images2kmz.image_processor import get_image_files

def main():
    input_dir = "./sample-images2"
    output_file = "descriptions.csv"
    
    # Get sorted list of images
    image_files = get_image_files(input_dir)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['File Number', 'Description'])
        
        for i, file_path in enumerate(image_files, 1):
            description = "NULL"
            try:
                with Image.open(file_path) as img:
                    exif_data = img.info.get('exif')
                    if exif_data:
                        exif_dict = piexif.load(exif_data)
                        desc_bytes = exif_dict.get('0th', {}).get(270)
                        if desc_bytes:
                            if isinstance(desc_bytes, bytes):
                                description = desc_bytes.decode('utf-8', errors='ignore').strip()
                            else:
                                description = str(desc_bytes).strip()
            except Exception:
                pass # Default to NULL on error
                
            writer.writerow([i, description])
    
    print(f"Created {output_file} with {len(image_files)} entries.")

if __name__ == "__main__":
    main()
