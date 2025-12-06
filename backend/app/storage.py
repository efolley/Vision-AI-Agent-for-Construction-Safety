import os
import io
import json
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from PIL import Image

Base = declarative_base()

class InspectionResult(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    original_filename = Column(String(255))
    violations = Column(JSON)                    # List of violations with code, desc, bbox
    violations_count = Column(Integer)
    image_original = Column(LargeBinary)         # Optional: keep original
    image_processed = Column(LargeBinary)        # Annotated image


class PostgresStorage:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not set in environment")

        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(self.engine)  # Creates table if not exists
        self.Session = sessionmaker(bind=self.engine)

    
    def save_result(
        self,
        original_filename: str,
        violations: List[Dict],
        annotated_image: Image.Image,
        original_image_bytes: bytes = None
    ) -> int:
        """
        Save one inspection result to PostgreSQL
        Returns the new record ID
        """
        # Convert annotated image to bytes
        buf = io.BytesIO()
        annotated_image.save(buf, format="JPEG")
        annotated_bytes = buf.getvalue()

        session = self.Session()
        try:
            result = InspectionResult(
                original_filename=original_filename,
                violations=violations,
                violations_count=len(violations),
                image_processed=annotated_bytes,
                image_original=original_image_bytes
            )
            session.add(result)
            session.commit()
            print(f"Saved inspection #{result.id} with {len(violations)} violations")
            return result.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent inspections for frontend history page"""
        session = self.Session()
        try:
            results = session.query(InspectionResult).order_by(InspectionResult.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "date": r.created_at.isoformat(),
                    "filename": r.original_filename,
                    "count": r.violations_count,
                    "violations": r.violations,
                    "image": r.image_processed  # bytes
                }
                for r in results
            ]
        finally:
            session.close()