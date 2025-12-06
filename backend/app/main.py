from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .agent import VisionAIOSHAgent
from PIL import Image
import io
import logging

# Optional: better error logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vision AI for Construction Safety",
    version="1.0",
    description="OSHA violation detection with Gemini 2.5 Flash + RAG"
)

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent once at startup — RAG loads only once
agent = VisionAIOSHAgent()

@app.get("/health")
async def health():
    return {"status": "healthy", "violations_in_db": "ready"}


@app.get("/")
async def root():
    return {"message": "OSHA Vision AI backend is running!"}


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        return JSONResponse(
            status_code=400,
            content={"error": "Only JPG/PNG images allowed"}
        )

    try:
        image_bytes = await file.read()
        if len(image_bytes) > 10_000_000:  # ~10MB limit
            return JSONResponse(status_code=400, content={"error": "Image too large"})

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Core AI processing
        violations, annotated_img = agent.analyze(image)

        # Convert result image to bytes
        buf = io.BytesIO()
        annotated_img.save(buf, format="JPEG", quality=95, optimize=True)
        img_bytes = buf.getvalue()

        logger.info(f"Processed {file.filename} → {len(violations)} violations")

        return {
            "violations": violations,
            "annotated_image_base64": img_bytes.hex(),
            "count": len(violations),
            "filename": file.filename
        }

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process image. Try again."}
        )