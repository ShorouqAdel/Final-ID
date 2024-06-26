from fastapi import FastAPI, File, UploadFile, Form
from typing import List, Optional, Union
import requests
from pydantic import BaseModel

app = FastAPI()

# Replace with your Bing Image Search API key
BING_IMAGE_SEARCH_API_KEY = 'af65f21bd3df4674baa51457191a956f'

IDENTIFY_PLANT_URL = 'https://graduation-project-2024.onrender.com/identify-plant'

class PlantIdentificationResult(BaseModel):
    scientific_name: str
    common_name: str
    probability: str
    description: str
    description_link: Optional[str]
    images: List[str]

class PlantIdentificationError(BaseModel):
    error: str

PlantResponse = Union[PlantIdentificationResult, PlantIdentificationError]
PlantsResponse = List[PlantResponse]

@app.post("/identify-plant-with-images", response_model=PlantsResponse)
async def identify_plant_with_images(organs: str = Form('auto'), image: UploadFile = File(...)):
    # Prepare data to send to the plant identification API
    files = {'image': (image.filename, image.file, image.content_type)}
    data = {'organs': organs}
    
    # Call the plant identification API
    response = requests.post(IDENTIFY_PLANT_URL, files=files, data=data)
    if response.status_code != 200:
        return [PlantIdentificationError(error=f"Error in plant identification API: {response.status_code}")]

    plant_data = response.json()
    if not plant_data.get("results"):
        return [PlantIdentificationError(error="Plant not identified")]

    # Extract relevant information for each plant
    plants_response = []
    for result in plant_data["results"]:
        scientific_name = result["scientific_name"]
        common_name = result["common_name"]
        probability = result["probability"]

        # Fetch description from Wikipedia
        wiki_search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{scientific_name}"
        wiki_response = requests.get(wiki_search_url)
        if wiki_response.status_code == 200:
            wiki_data = wiki_response.json()
            description = wiki_data.get("extract", "Description not found")
            description_link = wiki_data.get("content_urls", {}).get("desktop", {}).get("page")
        else:
            description = "Description not found"
            description_link = None

        # Search for images of the plant using Bing Image Search API with scientific name
        search_url = f"https://api.bing.microsoft.com/v7.0/images/search?q={scientific_name}+plant"
        headers = {
            "Ocp-Apim-Subscription-Key": BING_IMAGE_SEARCH_API_KEY,
            "Accept": "application/json"
        }
        search_response = requests.get(search_url, headers=headers)
        if search_response.status_code != 200:
            return [PlantIdentificationError(error=f"Error in Bing Image Search API: {search_response.status_code}")]

        images = [img["contentUrl"] for img in search_response.json().get("value", [])[:1]]

        # Add plant identification result to response list
        plants_response.append(PlantIdentificationResult(
            scientific_name=scientific_name, 
            common_name=common_name, 
            probability=probability, 
            description=description,
            description_link=description_link,
            images=images
        ))

    # Return the identification results as a list of Pydantic models
    return plants_response

@app.head("/ping")
async def ping():
    return "Hello, I am alive"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
