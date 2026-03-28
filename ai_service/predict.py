"""
Aqua AI Service — Prediction Functions
Model 1: XGBoost real-time classifier (Good / Warning / Risk)
Model 2: LSTM 6-hour recursive forecaster
"""

import os
import numpy as np
import pandas as pd
import joblib
import tensorflow as tf

# ── Load models at startup ─────────────────────────────────────────────────

# BASE = os.path.join(os.path.dirname(__file__), "models")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

model_1      = joblib.load(os.path.join(MODELS_DIR, "aqua_model1_final.pkl"))
scaler_1     = joblib.load(os.path.join(MODELS_DIR, "aqua_model1_scaler_final.pkl"))
model_2      = tf.keras.models.load_model(os.path.join(MODELS_DIR, "aqua_model2_1hrPred_final.keras"))
scaler_2     = joblib.load(os.path.join(MODELS_DIR, "aqua_model2_scaler_1hrPred_final.pkl"))

FEATURES_1 = ["Temp", "Turbidity", "DO", "pH", "Ammonia", "Nitrite"]
FEATURES_2 = ["temp", "do", "ph", "ammonia"]
LABEL_MAP  = {0: "Good", 1: "Warning", 2: "Risk"}


#H: the CTA message logic, as Risk has different actions to be taken depending on the parameters' impact

def get_specific_cta(temp, turbidity, do, ph, ammonia, nitrite, prediction):
   #H : when the prediction(by the classification model1) is Good there is no specific cta 
    if prediction == 0:
        return {
            "status":  "Good",
            "issues":  "All parameters normal",
            "actions": "No action needed. Continue monitoring.",
        }

    issues, actions = [], []

    #H: we define the issues and actions while evaluating each of the parameters' normality (the comparison values depend on the healthy values of offshores in general)
    if do < 3.5:
        issues.append(f"DO critically low ({do:.2f} mg/L)")
        actions.append("Activate aeration pump immediately")
    elif do < 6.0:
        issues.append(f"DO dropping ({do:.2f} mg/L)")
        actions.append("Check and increase aeration")

    if temp > 31:
        issues.append(f"Temperature critically high ({temp:.2f}\u00b0C)")
        actions.append("Increase water circulation")
    elif temp > 28:
        issues.append(f"Temperature elevated ({temp:.2f}\u00b0C)")
        actions.append("Monitor temperature closely")
    elif temp < 10:
        issues.append(f"Temperature critically low ({temp:.2f}\u00b0C)")
        actions.append("Check heating system immediately")
    elif temp < 14:
        issues.append(f"Temperature dropping ({temp:.2f}\u00b0C)")
        actions.append("Monitor temperature closely")

    if ammonia > 0.5:
        issues.append(f"Ammonia critically high ({ammonia:.2f} mg/L)")
        actions.append("Stop feeding immediately. Perform partial water change.")
    elif ammonia > 0.2:
        issues.append(f"Ammonia elevated ({ammonia:.2f} mg/L)")
        actions.append("Reduce feeding. Increase water flow.")

    if ph < 6.8:
        issues.append(f"pH critically low ({ph:.2f})")
        actions.append("Add buffering agent. Check CO2 levels.")
    elif ph > 9.2:
        issues.append(f"pH critically high ({ph:.2f})")
        actions.append("Increase aeration. Check for algal bloom.")
    elif ph < 7.2:
        issues.append(f"pH slightly low ({ph:.2f})")
        actions.append("Monitor pH trend closely.")
    elif ph > 8.8:
        issues.append(f"pH slightly high ({ph:.2f})")
        actions.append("Monitor for algal bloom signs.")

    if turbidity > 35:
        issues.append(f"Turbidity critically high ({turbidity:.2f} NTU)")
        actions.append("Check for algal bloom or pollution. Alert INRH.")
    elif turbidity > 20:
        issues.append(f"Turbidity elevated ({turbidity:.2f} NTU)")
        actions.append("Monitor water clarity. Check upstream pollution.")

    if nitrite > 2.0:
        issues.append(f"Nitrite critically high ({nitrite:.2f} mg/L)")
        actions.append("Stop feeding. Perform emergency water change.")
    elif nitrite > 1.0:
        issues.append(f"Nitrite elevated ({nitrite:.2f} mg/L)")
        actions.append("Reduce feeding rate. Improve biofiltration.")

    if not issues:
        issues.append("Multiple parameters in borderline range")
        actions.append("Full farm inspection required")

    return {
        "status":  "Risk" if prediction == 2 else "Warning",
        "issues":  " | ".join(issues),
        "actions": " | ".join(actions),
    }



#H: model 1 function: it uses model1 to classify the current water quality status
def predict_current(data: dict) -> dict:
    """
    input data: temp, turbidity, do, ph, ammonia, nitrite
    """
    df = pd.DataFrame([[
        data["temp"], data["turbidity"], data["do"],
        data["ph"], data["ammonia"], data["nitrite"]
    ]], columns=FEATURES_1)

    scaled     = scaler_1.transform(df)
    prediction = int(model_1.predict(scaled)[0])
    proba      = model_1.predict_proba(scaled)[0]
    cta        = get_specific_cta(
        data["temp"], data["turbidity"], data["do"],
        data["ph"], data["ammonia"], data["nitrite"],
        prediction
    )

    return {
        "current_status": LABEL_MAP[prediction],
        "confidence":     f"{round(float(proba[prediction]) * 100, 1)}%",
        "issues":         cta["issues"],
        "actions":        cta["actions"],
        "probabilities": {
            "Good":    f"{round(float(proba[0]) * 100, 1)}%",
            "Warning": f"{round(float(proba[1]) * 100, 1)}%",
            "Risk":    f"{round(float(proba[2]) * 100, 1)}%",
        },
    }


#H: model 2 function: it uses model2 to predict the future values of (temp/do/ph/ammonia) and water quality status
def predict_forecast(data: dict) -> dict:
    """
    Predict water quality for next n_hours using recursive LSTM.
    input: history (list of the last 24hrs data with temp/do/ph/ammonia),
               current_ammonia, current_nitrite, current_turbidity, n_hours
    """
    history          = pd.DataFrame(data["history"])[FEATURES_2].values
    current_ammonia  = data["current_ammonia"]
    current_nitrite  = data["current_nitrite"]
    current_turbidity = data["current_turbidity"]
    n_hours          = data.get("n_hours", 6)

    forecast = []

    for hour in range(1, n_hours + 1):
        window = history[-24:]
        scaled = scaler_2.transform(window)
        X      = scaled.reshape(1, 24, 4)

        pred_scaled = model_2.predict(X, verbose=0)
        pred_real   = scaler_2.inverse_transform(pred_scaled)[0]

        future_temp = float(pred_real[0])
        future_do   = float(pred_real[1])
        future_ph   = float(pred_real[2])

        #H: after getting the values predicted, we call the model 1 to see the status
        status = predict_current({
            "temp":      future_temp,
            "turbidity": current_turbidity,
            "do":        future_do,
            "ph":        future_ph,
            "ammonia":   current_ammonia,
            "nitrite":   current_nitrite,
        })

        forecast.append({
            "hour":    hour,
            "temp":    round(future_temp, 2),
            "do":      round(future_do, 2),
            "ph":      round(future_ph, 2),
            "ammonia": round(current_ammonia, 2),
            "status":  status["current_status"],
            "issues":  status["issues"],
            "actions": status["actions"],
        })

        #H: next iterations
        new_row = np.array([[future_temp, future_do, future_ph, current_ammonia]])
        history = np.vstack([history, new_row])

    return {"forecast": forecast}