# hybrid-api/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import statistics
import os

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION: The Team of Experts ---
# REPLACE THESE placeholders with your ACTUAL Render URLs
# Ensure they end with /predict/
API_URLS = {
    "xgboost": "https://xg-boost-model.onrender.com/predict/",
    "randomforest": "https://randomforestmodel-latest.onrender.com/predict/",
    "catboost": "https://catboost-model.onrender.com/predict/"
}

@app.route('/predict/', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        print(f"Hybrid Manager received request for: {data.get('coordinates')}")
        
        # Containers for the votes
        congestion_votes = []
        speed_votes = []
        volume_votes = []
        successful_models = []

        # 1. Ask the Experts (Sequential calls)
        for name, url in API_URLS.items():
            try:
                # We forward the exact same data payload
                response = requests.post(url, json=data, timeout=8)
                
                if response.status_code == 200:
                    result = response.json()
                    preds = result.get("predictions", {})
                    
                    # Collect Congestion (0-1)
                    if "congestion" in preds and "level" in preds["congestion"]:
                        congestion_votes.append(preds["congestion"]["level"])
                        
                    # Collect Speed
                    if "avgSpeed" in preds:
                        speed_votes.append(preds["avgSpeed"])

                    # Collect Volume (if available, mostly for CatBoost)
                    if "predictedVolume" in preds:
                        volume_votes.append(preds["predictedVolume"])
                        
                    successful_models.append(name)
                    print(f"✅ {name} responded.")
                else:
                    print(f"❌ {name} failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error calling {name}: {e}")

        # 2. Aggregation Logic (The "Wisdom of the Crowd")
        if not congestion_votes:
            return jsonify({"error": "All sub-models failed to respond"}), 500

        # Average the results
        avg_congestion = statistics.mean(congestion_votes)
        avg_speed = statistics.mean(speed_votes)
        
        # Volume is optional (XGB/RF might not send it), so handle carefully
        avg_volume = statistics.mean(volume_votes) if volume_votes else 0
        
        # 3. Interpret the Final Result
        congestion_label = "Low"
        if avg_congestion > 0.4: congestion_label = "Moderate"
        if avg_congestion > 0.7: congestion_label = "High"
        if avg_congestion > 0.9: congestion_label = "Severe"

        # 4. Final Response Structure
        response = {
            "predictions": {
                "congestion": {
                    "level": round(avg_congestion, 2),
                    "label": congestion_label
                },
                "avgSpeed": round(avg_speed),
                "predictedVolume": round(avg_volume)
            },
            "alternativeRoute": None, 
            "components": successful_models, # Debug info: who contributed?
            "modelUsed": "Hybrid Ensemble (Average)"
        }
        
        return jsonify(response)

    except Exception as e:
        print("Hybrid Error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Hybrid API is running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8005)