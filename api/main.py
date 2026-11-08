from fastapi import FastAPI

from api.routers import features, health

app = FastAPI(
    title="Feature store bancaire",
    description="Récupération des variables partagées par les modèles de la banque.",
    version="0.1.0",
)
app.include_router(health.router)
app.include_router(features.router)
