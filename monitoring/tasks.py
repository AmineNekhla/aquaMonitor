import logging
from celery import shared_task
from monitoring.ai_inference import run_inference_all_ponds

logger = logging.getLogger(__name__)

@shared_task
def periodic_inference():
    """
    1. Gets all active ponds
    2. Calls Model 1 (classification) on latest sensor readings
    3. Calls Model 2 (LSTM forecast) to generate 6-hour predictions
    4. Saves Forecast objects to database
    5. Creates Alerts if Warning/Risk status detected
    
    Returns:
        list: Results from run_inference_all_ponds()
    """
    try:
        logger.info("--- Starting periodic inference task ---")
        results = run_inference_all_ponds(save_forecast=True)
        logger.info(f"--- Inference complete. Processed {len(results)} ponds. ---")
        return results
    except Exception as e:
        logger.error(f"--- Inference task failed: {str(e)} ---", exc_info=True)
        raise
    
    
    


#H: for model 3
@shared_task
def periodic_disease_detection():
    """
    Periodic task: Scan video feeds/uploaded videos for diseases.
    Runs every 30 minutes.
    """
    try:
        from monitoring.disease_classifier import get_disease_classifier
        from monitoring.video_processor import VideoFrameExtractor
        from monitoring.models import Pond, Camera
        import os
        from django.conf import settings
        
        logger.info("Starting disease detection scanning...")
        
        classifier = get_disease_classifier()
        if not classifier or not classifier.classifier:
            logger.error("Disease classifier not available")
            return {'status': 'failed', 'reason': 'classifier_unavailable'}
        
        # Get all active ponds with cameras
        ponds_with_cameras = Pond.objects.filter(
            active=True,
            camera__isnull=False
        ).distinct()
        
        results = {
            'ponds_scanned': 0,
            'detections': 0,
            'alerts_created': 0,
        }
        
        for pond in ponds_with_cameras:
            # Get latest camera for pond
            camera = pond.camera_set.first()
            
            if not camera:
                continue
            
            try:
                # Check if there's a recent uploaded video
                video_path = camera.video_file.path if camera.video_file else None
                
                if video_path and os.path.exists(video_path):
                    # Extract frames from video
                    frames = VideoFrameExtractor.extract_frames_from_file(
                        video_path,
                        frame_interval=30  # Every 30th frame
                    )
                    
                    # Classify each frame
                    for frame_data in frames:
                        frame = frame_data['frame']
                        
                        result = classifier.classify_frame(
                            frame,
                            pond_id=pond.id,
                            camera_id=camera.id
                        )
                        
                        if result and result['disease_type'] != 'healthy':
                            results['detections'] += 1
                            logger.warning(f" Disease detected: {result}")
                else:
                    # Try to capture from live camera
                    frames = VideoFrameExtractor.extract_frames_from_camera(
                        camera_id=0,
                        num_frames=3
                    )
                    
                    for frame_data in frames:
                        frame = frame_data['frame']
                        
                        result = classifier.classify_frame(
                            frame,
                            pond_id=pond.id,
                            camera_id=camera.id
                        )
                        
                        if result and result['disease_type'] != 'healthy':
                            results['detections'] += 1
                
                results['ponds_scanned'] += 1
            
            except Exception as e:
                logger.error(f"Error scanning pond {pond.name}: {str(e)}")
                continue
        
        logger.info(f"Disease detection complete: {results}")
        return results
    
    except Exception as e:
        logger.error(f"Disease detection task failed: {str(e)}", exc_info=True)
        raise