# src/api/models/settingsModel.py
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field,JSON
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel


# --------------------------------------------------------------------
# MAIN MODEL
# --------------------------------------------------------------------
class Settings(TimeStampedModel, table=True):
    __tablename__ = "settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    options: Dict[str, Any] = Field(default={}, sa_type=JSON)  # JSON field for all settings
    language: str = Field(default="en", index=True)  # Language code

    class Config:
        arbitrary_types_allowed = True


# --------------------------------------------------------------------
# CRUD SCHEMAS
# --------------------------------------------------------------------
class SettingsCreate(SQLModel):
    options: Dict[str, Any] = {}
    language: Optional[str] = "en"


class SettingsRead(TimeStampReadModel):
    id: int
    options: Dict[str, Any]
    language: str


class SettingsUpdate(SQLModel):
    options: Optional[Dict[str, Any]] = None
    language: Optional[str] = None


# --------------------------------------------------------------------
# SPECIFIC SETTING SCHEMAS (For partial updates)
# --------------------------------------------------------------------
class GeneralSettingsUpdate(SQLModel):
    siteTitle: Optional[str] = None
    siteSubtitle: Optional[str] = None
    currency: Optional[str] = None
    freeShipping: Optional[bool] = None
    freeShippingAmount: Optional[int] = None
    minimumOrderAmount: Optional[int] = None


class DeliveryTimeSlot(SQLModel):
    title: str
    description: str


class DeliverySettingsUpdate(SQLModel):
    deliveryTime: Optional[list[DeliveryTimeSlot]] = None


class ContactLocation(SQLModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    formattedAddress: Optional[str] = None


class SocialLink(SQLModel):
    url: str
    icon: str


class ContactSettingsUpdate(SQLModel):
    contact: Optional[str] = None
    emailAddress: Optional[str] = None
    website: Optional[str] = None
    location: Optional[ContactLocation] = None
    socials: Optional[list[SocialLink]] = None


class SeoSettingsUpdate(SQLModel):
    metaTitle: Optional[str] = None
    metaDescription: Optional[str] = None
    metaTags: Optional[str] = None
    canonicalUrl: Optional[str] = None
    ogTitle: Optional[str] = None
    ogDescription: Optional[str] = None
    ogImage: Optional[str] = None
    twitterHandle: Optional[str] = None
    twitterCardType: Optional[str] = None


class PaymentGateway(SQLModel):
    name: str
    title: str


class PaymentSettingsUpdate(SQLModel):
    paymentGateway: Optional[list[PaymentGateway]] = None
    useCashOnDelivery: Optional[bool] = None
    useEnableGateway: Optional[bool] = None