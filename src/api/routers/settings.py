# src/api/routes/settings.py
from fastapi import APIRouter
from sqlmodel import select
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.settingsModel import (
    Settings, SettingsCreate, SettingsUpdate, SettingsRead,
    GeneralSettingsUpdate, DeliverySettingsUpdate, ContactSettingsUpdate,
    SeoSettingsUpdate, PaymentSettingsUpdate, DeliveryTimeSlot
)

router = APIRouter(prefix="/settings", tags=["Settings"])


# ✅ GET SETTINGS (Public - with language support)
@router.get("")
def get_settings(
    session: GetSession,
    language: str = "en"
):
    """Get settings for specific language, fallback to English if not found"""
    # Use SQLModel's select with session.exec properly
    statement = select(Settings).where(Settings.language == language)
    settings = session.exec(statement).first()
    
    # Fallback to English if language-specific settings not found
    if not settings and language != "en":
        statement = select(Settings).where(Settings.language == "en")
        settings = session.exec(statement).first()
    
    # Create default settings if none exist
    if not settings:
        default_settings = {
            "siteTitle": "Pickbazar",
            "siteSubtitle": "Your next ecommerce",
            "currency": "USD",
            "deliveryTime": [],
            "contactDetails": {
                "contact": "",
                "emailAddress": "",
                "website": "",
                "location": {
                    "lat": 0,
                    "lng": 0,
                    "formattedAddress": ""
                },
                "socials": []
            },
            "paymentGateway": [],
            "seo": {},
            "freeShipping": False,
            "freeShippingAmount": 0,
            "minimumOrderAmount": 0,
            "useCashOnDelivery": True,
            "useEnableGateway": False
        }
        settings = Settings(options=default_settings, language=language)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    
    # Convert to dictionary for response
    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }
    
    return api_response(200, "Settings retrieved successfully", settings_dict)


# ✅ CREATE SETTINGS
@router.post("/create")
def create_settings(
    session: GetSession,
    request: SettingsCreate,
    user=requirePermission("settings:create")
):
    # Check if settings for this language already exist
    statement = select(Settings).where(Settings.language == request.language)
    existing_settings = session.exec(statement).first()
    
    if existing_settings:
        return api_response(400, f"Settings for language '{request.language}' already exist")

    settings = Settings(**request.model_dump())
    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(201, "Settings created successfully", settings_dict)


# ✅ UPDATE FULL SETTINGS
@router.put("/update/{id}")
def update_settings(
    session: GetSession,
    id: int,
    request: SettingsUpdate,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Manual update
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)

    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "Settings updated successfully", settings_dict)


# ✅ UPDATE GENERAL SETTINGS
@router.patch("/update-general/{id}")
def update_general_settings(
    session: GetSession,
    id: int,
    request: GeneralSettingsUpdate,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Update only the general settings fields
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        settings.options[key] = value

    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "General settings updated successfully", settings_dict)


# ✅ UPDATE DELIVERY SETTINGS
@router.patch("/update-delivery/{id}")
def update_delivery_settings(
    session: GetSession,
    id: int,
    request: DeliverySettingsUpdate,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Update delivery time slots
    if request.deliveryTime is not None:
        settings.options["deliveryTime"] = [slot.model_dump() for slot in request.deliveryTime]

    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "Delivery settings updated successfully", settings_dict)


# ✅ UPDATE CONTACT SETTINGS
@router.patch("/update-contact/{id}")
def update_contact_settings(
    session: GetSession,
    id: int,
    request: ContactSettingsUpdate,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Initialize contactDetails if not exists
    if "contactDetails" not in settings.options:
        settings.options["contactDetails"] = {}

    # Update contact details
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        settings.options["contactDetails"][key] = value

    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "Contact settings updated successfully", settings_dict)


# ✅ UPDATE SEO SETTINGS
@router.patch("/update-seo/{id}")
def update_seo_settings(
    session: GetSession,
    id: int,
    request: SeoSettingsUpdate,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Initialize seo if not exists
    if "seo" not in settings.options:
        settings.options["seo"] = {}

    # Update SEO settings
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        settings.options["seo"][key] = value

    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "SEO settings updated successfully", settings_dict)


# ✅ UPDATE PAYMENT SETTINGS
@router.patch("/update-payment/{id}")
def update_payment_settings(
    session: GetSession,
    id: int,
    request: PaymentSettingsUpdate,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Update payment settings
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "paymentGateway" and value is not None:
            settings.options[key] = [gateway.model_dump() for gateway in value]
        else:
            settings.options[key] = value

    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "Payment settings updated successfully", settings_dict)


# ✅ DELETE SETTINGS
@router.delete("/delete/{id}")
def delete_settings(
    session: GetSession,
    id: int,
    user=requirePermission("settings:delete")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Prevent deletion of default English settings
    if settings.language == "en":
        return api_response(400, "Cannot delete default English settings")

    session.delete(settings)
    session.commit()
    return api_response(200, f"Settings deleted successfully")


# ✅ LIST ALL SETTINGS (Admin)
@router.get("/list")
def list_settings(
    session: GetSession,
    query_params: ListQueryParams,
    user=requirePermission("settings:view_all")
):
    query_params = vars(query_params)
    searchFields = ["language"]
    
    result = listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Settings,
        Schema=SettingsRead,
    )
    
    return result


# ✅ GET SETTING BY LANGUAGE
@router.get("/language/{language}")
def get_settings_by_language(
    session: GetSession,
    language: str
):
    statement = select(Settings).where(Settings.language == language)
    settings = session.exec(statement).first()
    
    raiseExceptions((settings, 404, f"Settings for language '{language}' not found"))

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "Settings retrieved successfully", settings_dict)


# ✅ ADD DELIVERY TIME SLOT
@router.post("/{id}/delivery-time")
def add_delivery_time_slot(
    session: GetSession,
    id: int,
    slot: DeliveryTimeSlot,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    # Initialize deliveryTime array if not exists
    if "deliveryTime" not in settings.options:
        settings.options["deliveryTime"] = []

    # Add new slot
    settings.options["deliveryTime"].append(slot.model_dump())
    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "Delivery time slot added successfully", settings_dict)


# ✅ REMOVE DELIVERY TIME SLOT
@router.delete("/{id}/delivery-time/{index}")
def remove_delivery_time_slot(
    session: GetSession,
    id: int,
    index: int,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    if "deliveryTime" not in settings.options or index >= len(settings.options["deliveryTime"]):
        return api_response(400, "Invalid delivery time slot index")

    # Remove the slot
    removed_slot = settings.options["deliveryTime"].pop(index)
    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, f"Delivery time slot '{removed_slot.get('title', '')}' removed successfully", settings_dict)


# ✅ UPDATE DELIVERY TIME SLOT
@router.put("/{id}/delivery-time/{index}")
def update_delivery_time_slot(
    session: GetSession,
    id: int,
    index: int,
    slot: DeliveryTimeSlot,
    user=requirePermission("settings:update")
):
    settings = session.get(Settings, id)
    raiseExceptions((settings, 404, "Settings not found"))

    if "deliveryTime" not in settings.options or index >= len(settings.options["deliveryTime"]):
        return api_response(400, "Invalid delivery time slot index")

    # Update the slot
    settings.options["deliveryTime"][index] = slot.model_dump()
    session.add(settings)
    session.commit()
    session.refresh(settings)

    settings_dict = {
        "id": settings.id,
        "options": settings.options,
        "language": settings.language,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }

    return api_response(200, "Delivery time slot updated successfully", settings_dict)


# ✅ GET SPECIFIC SETTING VALUE
@router.get("/value/{key}")
def get_setting_value(
    session: GetSession,
    key: str,
    language: str = "en"
):
    statement = select(Settings).where(Settings.language == language)
    settings = session.exec(statement).first()
    
    if not settings:
        return api_response(404, f"Settings for language '{language}' not found")

    value = settings.options.get(key)
    if value is None:
        return api_response(404, f"Setting '{key}' not found")

    return api_response(200, f"Setting '{key}' retrieved successfully", value)


# ✅ BULK UPDATE SETTINGS (for React form)
@router.put("/bulk-update")
def bulk_update_settings(
    session: GetSession,
    request: dict,
    user=requirePermission("settings:update")
):
    """Bulk update settings from React form data"""
    try:
        language = request.get("language", "en")
        options = request.get("options", {})
        
        # Find settings by language
        statement = select(Settings).where(Settings.language == language)
        settings = session.exec(statement).first()
        
        if not settings:
            # Create new settings if not found
            settings = Settings(options=options, language=language)
            session.add(settings)
        else:
            # Update existing settings
            settings.options = {**settings.options, **options}
            session.add(settings)
        
        session.commit()
        session.refresh(settings)
        
        settings_dict = {
            "id": settings.id,
            "options": settings.options,
            "language": settings.language,
            "created_at": settings.created_at,
            "updated_at": settings.updated_at
        }
        
        return api_response(200, "Settings updated successfully", settings_dict)
        
    except Exception as e:
        session.rollback()
        return api_response(500, f"Error updating settings: {str(e)}")