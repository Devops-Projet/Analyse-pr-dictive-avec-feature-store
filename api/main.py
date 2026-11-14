from fastapi import FastAPI

from api import metrics
from api.routers import features, health, predict

app = FastAPI(
    title="Feature store bancaire",
    description=(
        "Récupération des variables partagées par les modèles de la banque "
        "et prédictions des modèles en production."
    ),
    version="0.1.0",
)
metrics.install(app)
app.include_router(health.router)
app.include_router(features.router)
app.include_router(predict.router)
