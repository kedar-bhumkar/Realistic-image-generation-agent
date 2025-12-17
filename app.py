import os
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import main

app = FastAPI(title="Nano Banana Pro API")

# Security Scheme
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies the Bearer token against the API_AUTH_TOKEN environment variable.
    """
    token = credentials.credentials
    expected_token = os.environ.get("API_AUTH_TOKEN")
    
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration missing (API_AUTH_TOKEN)"
        )
    
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

class RunRequest(BaseModel):
    save_remotely: bool = True
    drive_folder_id: Optional[str] = "1H4wWGNaY01skMzUvQtQmHWlabaTc4rHx"
    category: Optional[str] = None
    min_val: Optional[int] = None
    max_val: Optional[int] = None
    resolution: Optional[str] = None
    aspect_ratio: Optional[str] = None
    mode: Optional[str] = "standard"
    model_version: Optional[str] = None
    image_urls: Optional[list[str]] = None
    prompts: Optional[list[str]] = None

def run_workflow(save_remotely: bool, drive_folder_id: str, category: Optional[str] = None, min_val: Optional[int] = None, max_val: Optional[int] = None, resolution: Optional[str] = None, aspect_ratio: Optional[str] = None, mode: str = "standard", model_version: Optional[str] = None, image_urls: Optional[list[str]] = None, prompts: Optional[list[str]] = None):
    """
    Wrapper to run the main logic. 
    Note: main.py currently prints to stdout and doesn't accept arguments easily,
    so we might need to modify main.py slightly or mock env vars if we want to pass args dynamically.
    For now, we just call main.main() which uses the logic defined there.
    """
    try:
        # We invoke the main function from main.py
        print(f"Triggering workflow via API. Remote Save: {save_remotely}, Category: {category}, Min: {min_val}, Max: {max_val}, Res: {resolution}, AR: {aspect_ratio}, Mode: {mode}, Model: {model_version}")
        main.main(
            save_remotely=save_remotely, 
            drive_folder_id=drive_folder_id, 
            category=category, 
            min_val=min_val, 
            max_val=max_val,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            mode=mode,
            model_version=model_version,
            image_urls=image_urls,
            prompts=prompts
        )
    except Exception as e:
        print(f"Error running workflow: {e}")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Nano Banana Pro API is ready."}

@app.post("/run", dependencies=[Depends(verify_token)])
def trigger_run(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Triggers the Nano Banana Pro workflow in the background.
    """
    # Run in background so the API response is immediate
    background_tasks.add_task(
        run_workflow, 
        request.save_remotely, 
        request.drive_folder_id, 
        request.category, 
        request.min_val, 
        request.max_val,
        request.resolution,
        request.aspect_ratio,
        request.mode,
        request.model_version,
        request.image_urls,
        request.prompts
    )
    return {"status": "accepted", "message": "Workflow started in background"}



