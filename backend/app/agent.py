import os
import io
import json
import google.generativeai as genai
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import re
import pathlib

from dotenv import load_dotenv
load_dotenv()


class VisionAIOSHAgent:
    def __init__(
        self,
        persist_dir: str = str(pathlib.Path(__file__).parent.parent / "RAG_vectorDB")
    ):
        # Gemini setup
        g_api_key = os.environ.get("GOOGLE_API_KEY")
        self.api_key = g_api_key or os.getenv("GOOGLE_API_KEY", g_api_key)
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash", 
                                           generation_config={"temperature": 0})

        self.persist_dir = persist_dir

        # RAG — build once, then just connect
        self._setup_rag()


    def _setup_rag(self):
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # Loading vectorstore
        vectorstore = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=embeddings
        )
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        total_documents = vectorstore._collection.count()
        print(f"Total documents in vectorstore: {total_documents}")


    def get_osha_reference(self, description: str) -> str:
        docs = self.retriever.invoke(description)
        return "\n\n".join(doc.page_content for doc in docs)


    @staticmethod
    def _pil_to_genai_image(pil_img: Image.Image):
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        buf.seek(0)
        return genai.upload_file(buf, mime_type="image/jpeg")


    @staticmethod
    def _draw_violations(image: Image.Image, violations: List[Dict]) -> Image.Image:
        img = image.convert("RGBA")
        overlay = Image.new("RGBA", 
                            img.size, 
                            (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        
        font = ImageFont.load_default(size=20)
        colors = ["#FF3333", "#33AA33", "#4444FF"]

        for i, v in enumerate(violations):
            box = v.get("bounding_box")
            if not box or len(box) != 4: continue
            x1,y1,x2,y2 = box
            
            if max(box) <= 1.0:
                w,h = image.size
                x1, y1, x2, y2 = int(x1*w), int(y1*h), int(x2*w), int(y2*h)

            color = colors[i % len(colors)]
            draw.rectangle([x1,y1,x2,y2], outline=color, width=7)

            code = v.get("code", "001")
            desc = v.get("title", "")

            # Show code only if RAG matched it
            if "NO CODE" not in code:
                draw.rectangle([x1, y1-55, x1+len(code)*13+20, y1-30], fill=color)
                draw.text((x1+10, y1-52), code, fill="white", font=font)

            draw.rectangle([x1, y1-28, x1+len(desc)*10+20, y1-5], fill=color)
            draw.text((x1+10, y1-25), desc, fill="white", font=font)

        return Image.alpha_composite(img, overlay).convert("RGB")


    def analyze(self, image: Image.Image) -> tuple[List[Dict], Image.Image]:
        genai_img = self._pil_to_genai_image(image)

        prompt = """You are an expert OSHA construction safety inspector with 20 years of field experience.

        Your job is to save lives — never miss a serious violation.

        Analyze this image and detect ALL visible OSHA violations.

        Rules:
        - Only report what you clearly see
        - Multiple workers = multiple violations
        - Be specific but short in description
        - Bounding box must tightly fit the violation (person, object, area)
        - Coordinates in pixels

        Return ONLY this exact JSON — nothing else, no markdown, no explanations:

        {
        "violations": [
            {
            "description": "<describe here the violation>",
            "bounding_box": [x_min, y_min, x_max, y_max]
            },
            {
            "description": "<describe here the violation>",
            "bounding_box": [x_min, y_min, x_max, y_max]
            }
        ]
        }

        If no violations → return: {"violations": []}
        """

        response = self.model.generate_content([prompt, genai_img])

        # Parse LLM output
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(text)
            detected_violations = data.get("violations", [])
        except:
            import re
            match = re.search(r'\[\s*{.*}\s*\]', text, re.DOTALL)
            detected_violations = json.loads(match.group()) if match else []

        # RAG-enhanced violations 
        enriched_violations = []
        for v in detected_violations:
            desc = v.get("description", "").lower().strip()
            bbox = v.get("bounding_box")

            if not desc or not bbox or len(bbox) != 4:
                continue

            results = self.retriever.invoke(desc)
            matched_code = None
            matched_title = None
            matched_text = None

            for doc in results:
                title = doc.metadata.get("title", "").lower()
                if any(word in title for word in desc.split() if len(word) > 3):
                    matched_code = doc.metadata.get("code")
                    matched_title = doc.metadata.get("title")
                    matched_text = doc.page_content
                    break

            violation = {
                "description": v["description"],
                "bounding_box": bbox
            }

            if matched_code:
                violation["code"] = matched_code
                violation["title"] = matched_title
                violation["osha_reference"] = matched_text[:800]

            enriched_violations.append(violation)

        # NEW: Deduplicate by OSHA code — keep only ONE entry per code
        seen_codes = set()
        final_violations = []

        for v in enriched_violations:
            code = v.get("code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                final_violations.append(v)
            elif not code:
                # Keep unmatched violations (no code)
                final_violations.append(v)

        # Draw
        annotated = self._draw_violations(image, final_violations)
        return final_violations, annotated