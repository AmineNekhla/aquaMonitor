"""
Test disease detection on a video file.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquaculture.settings')
django.setup()

from monitoring.disease_classifier import get_disease_classifier
from monitoring.video_processor import VideoFrameExtractor
from monitoring.models import Pond
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_disease_detection_on_video(video_path, pond_id=13):
    """
    Test disease detection on a video file.
    
    Args:
        video_path: Path to video file (relative or absolute)
        pond_id: Pond ID to associate detections with
    """
    
    print("=" * 70)
    print("🎬 DISEASE DETECTION TEST ON VIDEO")
    print("=" * 70)
    
    # Check if video exists
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Please place video in: {os.path.abspath('videos/test_videos/')}")
        return
    
    print(f"\n✅ Video found: {video_path}")
    
    # Check if pond exists
    # try:
    #     pond = Pond.objects.get(id=pond_id)
    #     print(f"✅ Pond found: {pond.name}")
    # except Pond.DoesNotExist:
    #     print(f"❌ Pond {pond_id} not found!")
    #     print("   Available ponds:")
    #     for p in Pond.objects.all():
    #         print(f"   - ID: {p.id}, Name: {p.name}")
    #     return
    
    # Initialize classifier
    print("\n🤖 Loading disease classifier...")
    classifier = get_disease_classifier()
    
    if not classifier or not classifier.classifier:
        print("❌ Failed to load classifier!")
        print("   Make sure dependencies are installed:")
        print("   pip install transformers torch torchvision opencv-python")
        return
    
    print("✅ Classifier loaded successfully")
    
    # Extract frames
    print(f"\n📸 Extracting frames from video (every 30th frame)...")
    frames = VideoFrameExtractor.extract_frames_from_file(
        video_path,
        frame_interval=30
    )
    
    if not frames:
        print("❌ No frames extracted from video!")
        return
    
    print(f"✅ Extracted {len(frames)} frames")
    
    # Classify each frame
    print(f"\n🔍 Running disease classification on {len(frames)} frames...")
    print("-" * 70)
    
    detections_count = 0
    disease_count = 0
    
    for idx, frame_data in enumerate(frames, 1):
        frame = frame_data['frame']
        timestamp = frame_data['timestamp']
        
        print(f"\n[Frame {idx}/{len(frames)}] Time: {timestamp:.1f}s")
        
        # Classify frame
        result = classifier.classify_frame(
            frame,
            pond_id=pond_id,
            camera_id=None
        )
        
        if result:
            detections_count += 1
            disease = result['disease_type']
            confidence = result['confidence']
            severity = result['severity']
            
            status_icon = "✅" if disease == 'healthy' else "⚠️"
            print(f"   {status_icon} Disease: {disease}")
            print(f"   📊 Confidence: {confidence:.1%}")
            print(f"   ⚠️  Severity: {severity}")
            
            if disease != 'healthy':
                disease_count += 1
                print(f"   🚨 DISEASE DETECTED!")
        else:
            print(f"   ❌ Classification failed")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Total frames processed: {len(frames)}")
    print(f"Successful classifications: {detections_count}")
    print(f"Disease detections: {disease_count}")
    print(f"Healthy frames: {detections_count - disease_count}")
    
    if detections_count > 0:
        disease_rate = (disease_count / detections_count) * 100
        print(f"Disease rate: {disease_rate:.1f}%")
    
    # Check database
    print(f"\n📁 Checking saved detections in database...")
    from monitoring.models import DiseaseDetection, DiseaseAlert
    
    db_detections = DiseaseDetection.objects.filter(pond_id=pond_id).order_by('-frame_timestamp')
    print(f"   Detections in database: {db_detections.count()}")
    
    if db_detections.exists():
        print(f"\n   Latest detections:")
        for detection in db_detections[:5]:
            print(f"   - {detection.disease_type} ({detection.confidence:.1%}) - {detection.frame_timestamp}")
    
    db_alerts = DiseaseAlert.objects.filter(pond_id=pond_id)
    print(f"\n   Alerts in database: {db_alerts.count()}")
    
    if db_alerts.exists():
        print(f"\n   Latest alerts:")
        for alert in db_alerts[:5]:
            print(f"   - {alert.disease_detection.disease_type}: {alert.message[:60]}...")
    
    print("\n✅ Test completed successfully!")
    print("=" * 70)


if __name__ == '__main__':
    # ===== CONFIGURATION =====
    
    # Video path (relative to project root)
    VIDEO_PATH = 'videos/test_videos/vid1.mp4'
    
    # Pond ID (use 1 if you have one pond)
    POND_ID = 1
    
    # ===== RUN TEST =====
    test_disease_detection_on_video(VIDEO_PATH, POND_ID)