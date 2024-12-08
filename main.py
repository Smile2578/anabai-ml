from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
from uuid import UUID, uuid4

app = FastAPI(title="AnabAI API")

class ScoreRequest(BaseModel):
    text: str
    context: str

class RecommendationRequest(BaseModel):
    user_id: str
    text: str

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/score/base")
async def calculate_base_score(request: ScoreRequest):
    try:
        # Simulation d'un calcul de score
        score = 0.75
        return {
            "id": str(uuid4()),
            "score": score,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/score/contextual")
async def calculate_contextual_score(request: ScoreRequest):
    try:
        # Simulation d'un calcul de score contextuel
        score = 0.85
        return {
            "id": str(uuid4()),
            "score": score,
            "context_factors": {
                "weather": 0.9,
                "time": 0.8,
                "crowd": 0.7
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommendations")
async def get_recommendations(request: RecommendationRequest):
    try:
        # Simulation de recommandations
        recommendations = [
            {
                "id": str(uuid4()),
                "title": "Recommandation 1",
                "score": 0.95,
                "context": {
                    "relevance": 0.9,
                    "popularity": 0.8
                }
            },
            {
                "id": str(uuid4()),
                "title": "Recommandation 2",
                "score": 0.85,
                "context": {
                    "relevance": 0.8,
                    "popularity": 0.9
                }
            }
        ]
        return {
            "user_id": request.user_id,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 