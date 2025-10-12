# src/api/models/product_model/importHistoryModel.py
from sqlmodel import SQLModel, Field, JSON, DateTime
from datetime import datetime
from typing import Optional, List, Dict, Any

class ProductImportHistory(SQLModel, table=True):
    __tablename__ = "product_import_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    original_filename: str
    file_size: int
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    status: str = "pending"  # pending, processing, completed, failed
    import_errors: Optional[List[Dict[str, Any]]] = Field(default=[], sa_type=JSON)
    imported_products: Optional[List[Dict[str, Any]]] = Field(default=[], sa_type=JSON)
    shop_id: int = Field(foreign_key="shops.id")
    imported_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None