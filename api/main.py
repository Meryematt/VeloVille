"""Point d'entrée de l'API VéloVille (FastAPI)."""

from fastapi import FastAPI

from api.routers import auth, incidents, indicateurs, stations, trajets

app = FastAPI(
    title="API VéloVille",
    description="Données des stations, trajets et incidents de VéloVille.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(stations.router)
app.include_router(trajets.router)
app.include_router(incidents.router)
app.include_router(indicateurs.router)


@app.get("/sante", tags=["Santé"])
def health():
    """Indique que l'API fonctionne."""

    return {"statut": "ok"}
