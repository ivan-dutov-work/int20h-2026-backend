from fastapi import APIRouter
import json
import os

router = APIRouter()

@router.get("/skills/")
async def get_skills():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    skills_path = os.path.join(base_dir, "scripts", "skills.json")
    
    if not os.path.exists(skills_path):
        return []
        
    with open(skills_path, "r") as f:
        data = json.load(f)
        
    return data
