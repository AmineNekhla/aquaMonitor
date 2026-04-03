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