from fastapi import FastAPI

app = FastAPI(title="OpsPilot API")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "OpsPilot backend is running"
    }