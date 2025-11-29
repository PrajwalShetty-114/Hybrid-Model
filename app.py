# hybrid-api/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import statistics
import os
import concurrent.futures

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION: The Team of Experts ---
# REPLACE THESE with your ACTUAL Render URLs
API_URLS = {
    "xgboost": "https://[YOUR-XGBOOST-URL].onrender.com/predict/",
    "randomforest": "https://[YOUR-RF-URL].onrender.com/predict/",
    "catboost": "https://[YOUR-CATBOOST-URL].onrender.com/predict/"
}

def call_model_api(name, url, payload):
    """
    Helper function to make a single API call.
    Returns (model_name, result_json) or (model_name, None) on failure.
    """
    try:
        # We assume all models accept the same standard payload structure
        response = requests.post(url, json=payload, timeout=8) # 8s timeout to prevent hanging
        if response.status_code == 200:
            return name, response.json()
        else:
            print(f"⚠️ {name} failed with status {response.status_code}")
            return name, None
    except Exception as e:
        print(f"❌ Error calling {name}: {e}")
        return name, None

@app.route('/predict/', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        # Log the request for debugging
        lat = data.get('coordinates', {}).get('lat')
        lng = data.get('coordinates', {}).get('lng')
        print(f"Hybrid Manager calculating for location: {lat}, {lng}")
        
        # --- 1. Query All Models in Parallel ---
        # Using ThreadPoolExecutor makes this much faster than sequential calls
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Start all requests at the same time
            future_to_model = {
                executor.submit(call_model_api, name, url, data): name 
                for name, url in API_URLS.items()
            }
            
            # Collect results as they finish
            for future in concurrent.futures.as_completed(future_to_model):
                name, result = future.result()
                if result:
                    results[name] = result

        # --- 2. Extract & Aggregate Data ---
        congestion_votes = []
        speed_votes = []
        volume_votes = []
        
        # XGBoost Vote
        if 'xgboost' in results:
            preds = results['xgboost'].get('predictions', {})
            if 'congestion' in preds: congestion_votes.append(preds['congestion']['level'])
            if 'avgSpeed' in preds: speed_votes.append(preds['avgSpeed'])
            
        # Random Forest Vote
        if 'randomforest' in results:
            preds = results['randomforest'].get('predictions', {})
            # RF might not return congestion level directly, but if it does, use it
            if 'congestion' in preds: congestion_votes.append(preds['congestion']['level'])
            if 'avgSpeed' in preds: speed_votes.append(preds['avgSpeed'])

        # CatBoost Vote
        if 'catboost' in results:
            preds = results['catboost'].get('predictions', {})
            if 'congestion' in preds: congestion_votes.append(preds['congestion']['level'])
            if 'avgSpeed' in preds: speed_votes.append(preds['avgSpeed'])
            if 'predictedVolume' in preds: volume_votes.append(preds['predictedVolume'])

        # --- 3. Compute Consensus ---
        if not congestion_votes and not speed_votes:
            return jsonify({"error": "All sub-models failed or returned invalid data"}), 500

        # Calculate Averages (The "Hybrid" Result)
        final_congestion = statistics.mean(congestion_votes) if congestion_votes else 0
        final_speed = statistics.mean(speed_votes) if speed_votes else 0
        final_volume = statistics.mean(volume_votes) if volume_votes else 0
        
        # Interpret the Final Congestion Level
        congestion_label = "Low"
        if final_congestion > 0.4: congestion_label = "Moderate"
        if final_congestion > 0.7: congestion_label = "High"
        if final_congestion > 0.9: congestion_label = "Severe"

        # --- 4. Final Response ---
        response = {
            "predictions": {
                "congestion": {
                    "level": round(final_congestion, 2),
                    "label": congestion_label
                },
                "avgSpeed": round(final_speed, 1),
                "predictedVolume": round(final_volume)
            },
            "alternativeRoute": None, # Could add logic to pick best alt route from subs
            "components": list(results.keys()), # List of models that successfully contributed
            "modelUsed": "Hybrid Ensemble (Average)"
        }
        
        print(f"Hybrid Result: Speed {final_speed}, Congestion {final_congestion}")
        return jsonify(response)

    except Exception as e:
        print("Hybrid Critical Error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Hybrid Ensemble API is running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8005)