"""
Video frame extraction for disease classification.
"""

import cv2
import numpy as np
import logging
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
import os

logger = logging.getLogger(__name__)

class VideoFrameExtractor:
    """Extract frames from video files or camera feeds."""
    
    @staticmethod
    def extract_frames_from_file(video_path, frame_interval=30):
        """
        As the model is classifying images, we need to extract frames from the video to feed into the model.
        Extract frames from a video file.
        
        Args:
            video_path: Path to video file
            frame_interval: Extract every Nth frame
        
        Returns:
            list: List of (frame, timestamp) tuples
        """
        
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return frames
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Extract every Nth frame
                if frame_count % frame_interval == 0:
                    # Convert BGR to RGB
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    timestamp = frame_count / fps  # seconds
                    frames.append({
                        'frame': rgb_frame,
                        'timestamp': timestamp,
                        'frame_number': frame_count
                    })
                
                frame_count += 1
        
        finally:
            cap.release()
        
        logger.info(f"Extracted {len(frames)} frames from video")
        return frames
    
    @staticmethod
    def extract_frames_from_camera(camera_id, num_frames=5, interval=1):
        """
        Capture frames from camera feed.
        
        Args:
            camera_id: Camera index (0 for default)
            num_frames: Number of frames to capture
            interval: Interval between captures (seconds)
        
        Returns:
            list: List of frames
        """
        
        frames = []
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            logger.error(f"Cannot open camera: {camera_id}")
            return frames
        
        try:
            frame_count = 0
            while len(frames) < num_frames:
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                if frame_count % (int(cap.get(cv2.CAP_PROP_FPS)) * interval) == 0:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append({
                        'frame': rgb_frame,
                        'timestamp': frame_count / cap.get(cv2.CAP_PROP_FPS),
                        'frame_number': frame_count
                    })
                
                frame_count += 1
        
        finally:
            cap.release()
        
        logger.info(f"Captured {len(frames)} frames from camera")
        return frames
    
    @staticmethod
    def frame_to_pil(frame):
        """Convert OpenCV frame to PIL Image."""
        if isinstance(frame, np.ndarray):
            return Image.fromarray(frame)
        return frame