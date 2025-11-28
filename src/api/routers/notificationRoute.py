# src/api/routes/notificationRoute.py
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select, and_
from datetime import datetime
import re
from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listRecords, updateOp
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireSignin,
    requirePermission,
)
from src.api.models.notificationModel import (
    Notification,
    NotificationCreate,
    NotificationUpdate,
    NotificationRead,
    NotificationMarkAsRead,
    NotificationBulkMarkAsRead
)

router = APIRouter(prefix="/notification", tags=["Notification"])


# Allowed HTML tags and attributes for message validation
ALLOWED_TAGS = ['a', 'b', 'strong', 'span', 'font']
ALLOWED_ATTRIBUTES = {
    'a': ['href'],
    'span': ['style'],
    'font': ['color', 'style'],
    'b': [],
    'strong': []
}


def validate_message(message: str) -> tuple[bool, str]:
    """
    Validate message content to only allow specific HTML tags and attributes.

    Allowed:
    - Plain text
    - <a href="...">link</a>
    - <b>bold text</b> or <strong>bold text</strong>
    - <font color="...">colored text</font>
    - <span style="color:...">colored text</span>

    Args:
        message: The message string to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not message or len(message.strip()) == 0:
        return False, "Message cannot be empty"

    if len(message) > 1000:
        return False, "Message must be 1000 characters or less"

    # Pattern to find all HTML tags
    tag_pattern = r'<([a-z]+)(\s+[^>]*)?>(.*?)</\1>|<([a-z]+)(\s+[^>]*)?\s*/?>'

    # Find all tags in the message
    tags = re.findall(r'</?([a-z]+)(?:\s+[^>]*)?\s*/?>', message, re.IGNORECASE)

    # Check if all tags are allowed
    for tag in tags:
        if tag.lower() not in ALLOWED_TAGS:
            return False, f"HTML tag '<{tag}>' is not allowed. Allowed tags: {', '.join(ALLOWED_TAGS)}"

    # Validate attributes for each tag
    full_tags = re.findall(r'<([a-z]+)(\s+[^>]+)?>', message, re.IGNORECASE)
    for tag_name, attributes_str in full_tags:
        tag_name = tag_name.lower()

        if attributes_str:
            # Extract attribute names
            attr_pattern = r'([a-z-]+)\s*=\s*["\']'
            attrs = re.findall(attr_pattern, attributes_str, re.IGNORECASE)

            allowed_attrs = ALLOWED_ATTRIBUTES.get(tag_name, [])
            for attr in attrs:
                if attr.lower() not in allowed_attrs:
                    return False, f"Attribute '{attr}' is not allowed for tag '<{tag_name}>'. Allowed attributes: {', '.join(allowed_attrs) if allowed_attrs else 'none'}"

    # Check for potentially dangerous content
    dangerous_patterns = [
        r'javascript:',
        r'on\w+\s*=',  # onclick, onload, etc.
        r'<script',
        r'<iframe',
        r'<object',
        r'<embed'
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return False, "Message contains potentially dangerous content"

    return True, ""


# ✅ CREATE Notification
@router.post("/create")
def create_notification(
    request: NotificationCreate,
    session: GetSession,
    user=requirePermission("notification:create"),
):
    """
    Create a new notification.

    Message can contain:
    - Plain text
    - <a href="url">link text</a>
    - <b>bold</b> or <strong>bold</strong>
    - <font color="#hex">colored text</font>
    - <span style="color:#hex">colored text</span>

    Maximum 1000 characters.
    """
    print("📢 Creating notification:", request.model_dump())

    # Validate message content
    is_valid, error_msg = validate_message(request.message)
    if not is_valid:
        return api_response(400, error_msg)

    # Check if user exists
    from src.api.models.usersModel import User
    user_exists = session.get(User, request.user_id)
    if not user_exists:
        return api_response(404, f"User with ID {request.user_id} not found")

    # Create notification
    notification = Notification(**request.model_dump())
    notification.sent_at = datetime.utcnow()

    session.add(notification)
    session.commit()
    session.refresh(notification)

    return api_response(
        201,
        "Notification created successfully",
        NotificationRead.model_validate(notification)
    )


# ✅ UPDATE Notification
@router.put("/update/{id}")
def update_notification(
    id: int,
    request: NotificationUpdate,
    session: GetSession,
    user=requirePermission("notification:update"),
):
    """Update notification message (only unread notifications can be updated)"""
    notification = session.get(Notification, id)
    raiseExceptions((notification, 404, "Notification not found"))

    # Don't allow updating read notifications
    if notification.is_read:
        return api_response(400, "Cannot update a notification that has been read")

    # Validate message if provided
    if request.message:
        is_valid, error_msg = validate_message(request.message)
        if not is_valid:
            return api_response(400, error_msg)

    updated = updateOp(notification, request, session)
    session.commit()
    session.refresh(updated)

    return api_response(
        200,
        "Notification updated successfully",
        NotificationRead.model_validate(updated)
    )


# ✅ READ Notification by ID
@router.get("/read/{id}")
def read_notification(
    id: int,
    session: GetSession,
    user: requireSignin
):
    """Get a specific notification by ID"""
    notification = session.get(Notification, id)
    raiseExceptions((notification, 404, "Notification not found"))

    # Check if user has access to this notification
    if notification.user_id != user.get("id") and not user.get("is_root"):
        return api_response(403, "You don't have access to this notification")

    return api_response(
        200,
        "Notification found",
        NotificationRead.model_validate(notification)
    )


# ✅ DELETE Notification
@router.delete("/delete/{id}")
def delete_notification(
    id: int,
    session: GetSession,
    user: requireSignin
):
    """Delete a notification"""
    notification = session.get(Notification, id)
    raiseExceptions((notification, 404, "Notification not found"))

    # Check if user has access to this notification
    if notification.user_id != user.get("id") and not user.get("is_root"):
        return api_response(403, "You don't have access to this notification")

    session.delete(notification)
    session.commit()

    return api_response(200, f"Notification deleted successfully")


# ✅ LIST User's Notifications
@router.get("/list", response_model=list[NotificationRead])
def list_notifications(
    query_params: ListQueryParams,
    user: requireSignin,
    session: GetSession,
):
    """List all notifications for the authenticated user"""
    query_params = vars(query_params)

    # Add user filter to only show their notifications
    query_params['customFilters'] = [['user_id', user.get("id")]]

    searchFields = ["message"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Notification,
        Schema=NotificationRead,
    )


# ✅ LIST ALL Notifications (Admin only)
@router.get("/list-all", response_model=list[NotificationRead])
def list_all_notifications(
    query_params: ListQueryParams,
    user=requirePermission("notification:view_all")
):
    """List all notifications (admin only)"""
    query_params = vars(query_params)
    searchFields = ["message"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Notification,
        Schema=NotificationRead,
    )


# ✅ MARK AS READ
@router.patch("/{id}/mark-as-read")
def mark_as_read(
    id: int,
    session: GetSession,
    user: requireSignin
):
    """Mark a notification as read with timestamp"""
    notification = session.get(Notification, id)
    raiseExceptions((notification, 404, "Notification not found"))

    # Check if user has access to this notification
    if notification.user_id != user.get("id"):
        return api_response(403, "You don't have access to this notification")

    # Don't update if already read
    if notification.is_read:
        return api_response(200, "Notification was already marked as read",
                          NotificationRead.model_validate(notification))

    # Mark as read with timestamp
    notification.is_read = True
    notification.read_at = datetime.utcnow()

    session.add(notification)
    session.commit()
    session.refresh(notification)

    return api_response(
        200,
        "Notification marked as read",
        NotificationRead.model_validate(notification)
    )


# ✅ MARK MULTIPLE AS READ
@router.patch("/bulk-mark-as-read")
def bulk_mark_as_read(
    request: NotificationBulkMarkAsRead,
    session: GetSession,
    user: requireSignin
):
    """Mark multiple notifications as read"""
    if not request.notification_ids:
        return api_response(400, "No notification IDs provided")

    # Get all notifications
    notifications = session.exec(
        select(Notification).where(
            and_(
                Notification.id.in_(request.notification_ids),
                Notification.user_id == user.get("id")
            )
        )
    ).all()

    if not notifications:
        return api_response(404, "No notifications found")

    # Mark all as read
    updated_count = 0
    current_time = datetime.utcnow()

    for notification in notifications:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = current_time
            session.add(notification)
            updated_count += 1

    session.commit()

    return api_response(
        200,
        f"{updated_count} notification(s) marked as read",
        {"updated_count": updated_count, "total_requested": len(request.notification_ids)}
    )


# ✅ MARK ALL AS READ
@router.patch("/mark-all-as-read")
def mark_all_as_read(
    session: GetSession,
    user: requireSignin
):
    """Mark all user's notifications as read"""
    # Get all unread notifications for the user
    notifications = session.exec(
        select(Notification).where(
            and_(
                Notification.user_id == user.get("id"),
                Notification.is_read == False
            )
        )
    ).all()

    if not notifications:
        return api_response(200, "No unread notifications to mark as read")

    # Mark all as read
    current_time = datetime.utcnow()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = current_time
        session.add(notification)

    session.commit()

    return api_response(
        200,
        f"{len(notifications)} notification(s) marked as read",
        {"updated_count": len(notifications)}
    )


# ✅ GET UNREAD COUNT
@router.get("/unread-count")
def get_unread_count(
    session: GetSession,
    user: requireSignin
):
    """Get count of unread notifications for the authenticated user"""
    from sqlalchemy import func

    count = session.scalar(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user.get("id"),
                Notification.is_read == False
            )
        )
    )

    return api_response(200, "Unread count retrieved", {"unread_count": count or 0})


# ✅ GET RECENT NOTIFICATIONS
@router.get("/recent")
def get_recent_notifications(
    session: GetSession,
    user: requireSignin,
    limit: int = Query(10, ge=1, le=50)
):
    """Get recent notifications for the authenticated user"""
    notifications = session.exec(
        select(Notification)
        .where(Notification.user_id == user.get("id"))
        .order_by(Notification.sent_at.desc())
        .limit(limit)
    ).all()

    return api_response(
        200,
        f"{len(notifications)} recent notification(s) retrieved",
        [NotificationRead.model_validate(n) for n in notifications]
    )
