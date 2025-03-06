import os
import base64
import tempfile
import cv2
import numpy as np
from moviepy.editor import ImageSequenceClip
from dash.dash_table.Format import Format, Scheme
import plotly.io as pio

class VideoRecorder:
    def __init__(self, fps=20, output_path=None):
        self.fps = fps
        self.frames = []
        self.output_path = output_path if output_path else "simulation_animation.mp4"
        self.temp_dir = tempfile.mkdtemp()
        
    def add_frame(self, figures):
        """Add a frame to the video by capturing plotly figures - optimized"""
        # Create a temporary directory for this frame
        frame_dir = os.path.join(self.temp_dir, f"frame_{len(self.frames)}")
        os.makedirs(frame_dir, exist_ok=True)
        
        # Get images for each figure
        images = []
        for i, fig in enumerate(figures):
            img_path = os.path.join(frame_dir, f"fig_{i}.png")
            
            # Reduce image quality for faster rendering
            pio.write_image(fig, img_path, scale=1.5)
            
            img = cv2.imread(img_path)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                images.append(img)
        
        # Skip frame if any images failed to load
        if len(images) != len(figures):
            print(f"WARNING: Skipping frame {len(self.frames)} due to missing images")
            return len(self.frames)
        
                    # Combine images into a single frame
        # For simplicity, we'll use a vertical stack here
        try:
            # Ensure all images have the same width
            max_width = max(img.shape[1] for img in images)
            resized_images = []
            
            for img in images:
                if img.shape[1] < max_width:
                    # Resize to match the maximum width
                    height, width = img.shape[:2]
                    new_height = int(height * (max_width / width))
                    resized = cv2.resize(img, (max_width, new_height))
                    resized_images.append(resized)
                else:
                    resized_images.append(img)
            
            frame = np.vstack(resized_images)
            self.frames.append(frame)
        except Exception as e:
            print(f"ERROR stacking images: {e}")
            # Create a blank frame if stacking fails
            blank_frame = np.ones((800, 1200, 3), dtype=np.uint8) * 255
            cv2.putText(blank_frame, f"Frame {len(self.frames)} Error", (400, 400), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            self.frames.append(blank_frame)
        
        return len(self.frames)
    
    def save_video(self):
        """Save frames as a video file - optimized for performance"""
        # Ensure we have frames to save
        if not self.frames:
            print("WARNING: No frames to save")
            # Create a dummy frame
            dummy_frame = np.ones((800, 1200, 3), dtype=np.uint8) * 255
            cv2.putText(dummy_frame, "No frames captured", (400, 400), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            self.frames.append(dummy_frame)
        
        try:
            # Check if all frames have the same dimensions
            heights = [frame.shape[0] for frame in self.frames]
            widths = [frame.shape[1] for frame in self.frames]
            
            if len(set(heights)) > 1 or len(set(widths)) > 1:
                print("WARNING: Frames have inconsistent dimensions, resizing...")
                # Resize all frames to match the first frame
                target_height, target_width = self.frames[0].shape[:2]
                for i in range(1, len(self.frames)):
                    if self.frames[i].shape[:2] != (target_height, target_width):
                        self.frames[i] = cv2.resize(self.frames[i], (target_width, target_height))
            
            # Create video with optimized settings
            clip = ImageSequenceClip(self.frames, fps=self.fps)
            clip.write_videofile(self.output_path, codec='libx264', 
                                audio=False, verbose=False, threads=4)
            
            return self.output_path
        except Exception as e:
            print(f"ERROR saving video: {e}")
            import traceback
            traceback.print_exc()
            
            # Try a more basic approach if the above fails
            print("Attempting alternative video creation method...")
            try:
                height, width, _ = self.frames[0].shape
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video = cv2.VideoWriter(self.output_path, fourcc, self.fps, (width, height))
                
                for frame in self.frames:
                    # Convert from RGB to BGR for OpenCV
                    bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    video.write(bgr_frame)
                
                video.release()
                return self.output_path
            except Exception as nested_e:
                print(f"ERROR in fallback video creation: {nested_e}")
                traceback.print_exc()
                return None
    
    def get_download_data(self):
        """Get the video file as base64 for downloading"""
        video_path = self.save_video()
        
        if not video_path or not os.path.exists(video_path):
            print("ERROR: Video file not created")
            return None
        
        try:
            with open(video_path, "rb") as file:
                video_data = file.read()
            
            encoded_video = base64.b64encode(video_data).decode()
            return encoded_video
        except Exception as e:
            print(f"ERROR encoding video: {e}")
            return None