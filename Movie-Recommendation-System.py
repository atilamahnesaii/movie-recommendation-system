#pip install flask
#pip install opencv-python-headless

from flask import Flask, render_template, request, redirect, url_for
import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Create necessary directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('static', exist_ok=True)

def enhance_frame(frame):
    """Enhance a single frame with color, sharpness, and brightness adjustments"""
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    # Apply enhancements
    enhancers = [
        (ImageEnhance.Color, 1.25),
        (ImageEnhance.Sharpness, 1.5),
        (ImageEnhance.Brightness, 1.05)
    ]
    
    for enhancer_class, factor in enhancers:
        img = enhancer_class(img).enhance(factor)
    
    # Apply unsharp mask for additional sharpness
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=2))
    
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def upscale_video(input_path, output_path, target_res=(1280, 720)):
    """Upscale video to 720p with enhanced quality"""
    cap = cv2.VideoCapture(input_path)
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, target_res)
    
    processed = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Resize to 720p using Lanczos interpolation
        frame_up = cv2.resize(frame, target_res, interpolation=cv2.INTER_LANCZOS4)
        
        # Enhance frame quality
        frame_up = enhance_frame(frame_up)
        
        out.write(frame_up)
        processed += 1
        
        # Progress indicator
        if processed % 50 == 0:
            print(f"Processed {processed}/{total_frames} frames")
    
    cap.release()
    out.release()
    
    return processed

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'video' not in request.files:
            return 'No file uploaded', 400
        
        file = request.files['video']
        if file.filename == '':
            return 'No file selected', 400
        
        if file:
            # Secure filename and save
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)
            
            # Process video
            output_filename = f"enhanced_{filename}"
            output_path = os.path.join('static', output_filename)
            
            try:
                frames_processed = upscale_video(input_path, output_path)
                
                return render_template('upload.html', 
                                     video_url=f"/static/{output_filename}",
                                     frames_processed=frames_processed,
                                     success=True)
            except Exception as e:
                return f"Error processing video: {str(e)}", 500
    
    return render_template('upload.html', success=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)