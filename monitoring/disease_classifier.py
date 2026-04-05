"""
Disease classification service using Hugging Face model.
Integrates fish/shrimp disease detection from video frames.
"""

import torch
import numpy as np
from PIL import Image
from io import BytesIO
import logging
from transformers import pipeline
from django.core.files.base import ContentFile
from monitoring.models import DiseaseDetection, DiseaseAlert, Pond

logger = logging.getLogger(__name__)

class DiseaseClassifier:
    """Wrapper for Hugging Face fish/shrimp disease classifier."""
    
    def __init__(self):
        """Initialize the disease classifier model."""
        try:
            # Load the Hugging Face model
            self.classifier = pipeline(
                "image-classification",
                model="Saon110/fish-shrimp-disease-classifier",
                device=0 if torch.cuda.is_available() else -1  # GPU if available
            )
            self.model_version = "huggingface-saon110-v1"
            logger.info("Disease classifier model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load disease classifier: {str(e)}")
            self.classifier = None
    
    def classify_frame(self, image_input, pond_id=None, camera_id=None):
        """
        Classify a single frame/image for diseases.
        
        Args:
            image_input: PIL Image, numpy array, or file path
            pond_id: Pond ID for database storage
            camera_id: Camera ID (optional)
        
        Returns:
            dict: Classification result with disease type, confidence, etc.
        """
        
        if self.classifier is None:
            logger.error("Classifier not initialized")
            return None
        
        try:
            # Convert input to PIL Image if needed
            if isinstance(image_input, str):
                # File path
                image = Image.open(image_input).convert('RGB')
            elif isinstance(image_input, np.ndarray):
                # NumPy array (from video frame)
                image = Image.fromarray(image_input.astype('uint8')).convert('RGB')
            elif isinstance(image_input, bytes):
                # Bytes
                image = Image.open(BytesIO(image_input)).convert('RGB')
            else:
                # Assume PIL Image
                image = image_input.convert('RGB')
            
            # Run inference
            results = self.classifier(image)
            
            logger.info(f"Classification results: {results}")
            
            # Parse results (format: [{'label': 'disease_name', 'score': 0.95}, ...])
            if results:
                top_result = results[0]  # Best match
                disease_label = top_result['label']
                confidence = float(top_result['score'])
                
                # Map Hugging Face labels to our disease choices
                disease_type = self._map_disease_label(disease_label)
                
                # Determine severity based on confidence
                severity = self._determine_severity(confidence, disease_type)
                
                result = {
                    'disease_type': disease_type,
                    'confidence': confidence,
                    'severity': severity,
                    'all_predictions': results,
                    'raw_label': disease_label,
                }
                
                # Save to database if pond_id provided
                if pond_id:
                    self._save_detection(
                        pond_id=pond_id,
                        camera_id=camera_id,
                        disease_type=disease_type,
                        confidence=confidence,
                        severity=severity,
                        image=image
                    )
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error during classification: {str(e)}")
            return None
    
    def _map_disease_label(self, huggingface_label):
        """Map Hugging Face model labels to our disease choices."""
        
        label_lower = huggingface_label.lower()
        
        # Map common disease names
        mapping = {
            'healthy': 'healthy',
            'spot': 'spot_disease',
            'white spot': 'white_spot',
            'bacterial': 'bacterial_infection',
            'fungal': 'fungal_infection',
            'parasitic': 'parasitic_infection',
            'parasite': 'parasitic_infection',
            'infection': 'bacterial_infection',  # Default to bacterial if unsure
            'disease': 'unknown',
        }
        
        for key, value in mapping.items():
            if key in label_lower:
                return value
        
        return 'unknown'
    
    def _determine_severity(self, confidence, disease_type):
        """Determine severity level based on confidence and disease type."""
        
        if disease_type == 'healthy':
            return 'mild'
        
        if confidence >= 0.85:
            return 'severe'
        elif confidence >= 0.70:
            return 'moderate'
        else:
            return 'mild'
    
    def _save_detection(self, pond_id, camera_id, disease_type, confidence, severity, image):
        """Save detection to database and create alert if needed."""
        
        try:
            pond = Pond.objects.get(id=pond_id)
            
            # Convert image to bytes for storage
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Create detection record
            detection = DiseaseDetection.objects.create(
                pond=pond,
                camera_id=camera_id,
                disease_type=disease_type,
                confidence=confidence,
                severity=severity,
                model_version=self.model_version,
            )
            
            # Save frame image
            detection.frame_image.save(
                f'disease_{pond_id}_{detection.id}.png',
                ContentFile(img_byte_arr.getvalue()),
                save=True
            )
            
            logger.info(f"Disease detection saved: {detection}")
            
            # Create alert if disease detected and confidence high
            if disease_type != 'healthy' and confidence >= 0.70:
                self._create_alert(detection, pond)
            
            return detection
            
        except Pond.DoesNotExist:
            logger.error(f"Pond {pond_id} not found")
        except Exception as e:
            logger.error(f"Error saving detection: {str(e)}")
    
    def _create_alert(self, detection, pond):
        """Create alert for disease detection."""
        
        try:
            alert_type = 'disease_detected'
            if detection.confidence >= 0.90:
                alert_type = 'high_confidence'
            
            alert_severity = 'high' if detection.confidence >= 0.85 else 'medium'
            
            message = (
                f"Disease detected in {pond.name}: {detection.disease_type} "
                f"(Confidence: {detection.confidence:.1%}, Severity: {detection.severity}). "
                f"Review the frame immediately."
            )
            
            alert = DiseaseAlert.objects.create(
                disease_detection=detection,
                pond=pond,
                alert_type=alert_type,
                message=message,
                severity=alert_severity,
            )
            
            logger.warning(f"Alert created: {alert}")
            
            return alert
            
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")


# Global instance
_classifier_instance = None

def get_disease_classifier():
    """Get or create the disease classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DiseaseClassifier()
    return _classifier_instance