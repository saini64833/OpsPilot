from fastapi import FastAPI
app = FastAPI(title="OpsPilot")
@app.get("/")
def root():
    return {
        "message": "OpsPilot backend is running"
    }