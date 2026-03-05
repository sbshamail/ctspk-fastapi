"""
Seed script for email templates (IDs 7–11).
Uses Unlayer editor JSON format for `content` and pre-rendered HTML for `html_content`.
Run once at startup — skips any template whose ID already exists.
"""
from sqlmodel import Session, select
from src.api.models.email_model.emailModel import Emailtemplate


# ---------------------------------------------------------------------------
# Unlayer design JSON + rendered HTML for each template
# ---------------------------------------------------------------------------

TEMPLATES = [
    # ------------------------------------------------------------------ #
    # 7 — Order Assigned to Fulfillment
    # ------------------------------------------------------------------ #
    {
        "id": 7,
        "name": "Order Assigned to Fulfillment",
        "slug": "order-assigned-fulfillment",
        "subject": "Order {{order_number}} has been assigned to you",
        "is_active": True,
        "language": "en",
        "content": {
            "counters": {"u_row": 4, "u_column": 4, "u_content_text": 4, "u_content_button": 1, "u_content_divider": 1},
            "body": {
                "id": "body",
                "rows": [
                    {
                        "id": "r1",
                        "cells": [1],
                        "columns": [{
                            "id": "c1",
                            "contents": [{
                                "id": "t1",
                                "type": "text",
                                "values": {
                                    "text": "<h2 style='color:#1a1a2e;margin:0 0 12px'>Fulfillment Assignment</h2><p style='color:#444;font-size:15px;line-height:1.6'>Hi <strong>{{fulfillment_name}}</strong>,</p><p style='color:#444;font-size:15px;line-height:1.6'>Order <strong>{{order_number}}</strong> has been assigned to you for fulfillment.</p><p style='color:#444;font-size:15px;line-height:1.6'><strong>Customer:</strong> {{customer_name}}<br><strong>Order ID:</strong> #{{order_id}}</p><p style='color:#444;font-size:15px;line-height:1.6'>Please log in to the system to process this order.</p>",
                                    "containerPadding": "20px 30px",
                                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                                    "fontSize": "15px",
                                    "lineHeight": "1.6",
                                    "textAlign": "left",
                                    "hideDesktop": False,
                                    "displayCondition": None,
                                    "_styleGuide": None
                                }
                            }],
                            "values": {"backgroundColor": "#ffffff", "padding": "0px", "border": {}, "borderRadius": "0px"}
                        }],
                        "values": {
                            "displayCondition": None,
                            "columns": False,
                            "backgroundColor": "#f4f4f4",
                            "columnsBackgroundColor": "#ffffff",
                            "backgroundImage": {"url": "", "fullWidth": True, "repeat": False, "center": True, "cover": False},
                            "padding": "20px 0px",
                            "anchor": "",
                            "hideDesktop": False,
                            "_styleGuide": None
                        }
                    }
                ],
                "headers": [],
                "footers": [],
                "values": {
                    "popupPosition": "center",
                    "popupWidth": "600px",
                    "popupHeight": "auto",
                    "borderRadius": "10px",
                    "contentAlign": "center",
                    "contentVerticalAlign": "center",
                    "contentWidth": 600,
                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                    "preheaderText": "Order {{order_number}} assigned to you",
                    "popupBackgroundColor": "#ffffff",
                    "popupBackgroundImage": {"url": "", "fullWidth": True, "repeat": False, "center": True, "cover": True},
                    "popupOverlay_backgroundColor": "rgba(0,0,0,0.1)",
                    "popupCloseButton_margin": "0px",
                    "popupCloseButton_position": "top-right",
                    "popupCloseButton_backgroundColor": "#cccccc",
                    "popupCloseButton_iconColor": "#000000",
                    "popupCloseButton_borderRadius": "0px",
                    "popupCloseButton_margin": "0px",
                    "backgroundColor": "#e9e9e9",
                    "backgroundImage": {"url": "", "fullWidth": True, "repeat": False, "center": True, "cover": False},
                    "defaultFontSize": "15px",
                    "linkStyle": {"body": True, "linkColor": "#0000ee", "linkHoverColor": "#0000ee", "linkUnderline": True, "linkHoverUnderline": True},
                    "_styleGuide": None
                }
            },
            "schemaVersion": 16
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fulfillment Assignment</title></head>
<body style="margin:0;padding:0;background:#e9e9e9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#e9e9e9;padding:20px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:10px;overflow:hidden;max-width:600px;">
      <tr><td style="background:#1a1a2e;padding:24px 30px;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:700;">CTSPK</h1>
      </td></tr>
      <tr><td style="padding:30px;">
        <h2 style="color:#1a1a2e;margin:0 0 16px;font-size:20px;">Fulfillment Assignment</h2>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Hi <strong>{{fulfillment_name}}</strong>,</p>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Order <strong>{{order_number}}</strong> has been assigned to you for fulfillment.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f8f9fa;border-radius:8px;padding:16px;margin:16px 0;">
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Order ID:</strong> #{{order_id}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Order Number:</strong> {{order_number}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Customer:</strong> {{customer_name}}</td></tr>
        </table>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:12px 0 0;">Please log in to the system to process this order promptly.</p>
      </td></tr>
      <tr><td style="background:#f8f9fa;padding:16px 30px;text-align:center;font-size:12px;color:#888;">
        &copy; CTSPK. All rights reserved.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    },

    # ------------------------------------------------------------------ #
    # 8 — Order Cancelled / Refunded
    # ------------------------------------------------------------------ #
    {
        "id": 8,
        "name": "Order Cancelled / Refunded",
        "slug": "order-cancelled-refunded",
        "subject": "Your Order {{order_number}} has been {{order_status}}",
        "is_active": True,
        "language": "en",
        "content": {
            "counters": {"u_row": 4, "u_column": 4, "u_content_text": 4},
            "body": {
                "id": "body",
                "rows": [
                    {
                        "id": "r1",
                        "cells": [1],
                        "columns": [{
                            "id": "c1",
                            "contents": [{
                                "id": "t1",
                                "type": "text",
                                "values": {
                                    "text": "<h2 style='color:#c0392b;margin:0 0 12px'>Order {{order_status}}</h2><p style='color:#444;font-size:15px;line-height:1.6'>Dear <strong>{{customer_name}}</strong>,</p><p style='color:#444;font-size:15px;line-height:1.6'>Your order <strong>{{order_number}}</strong> (ID: #{{order_id}}) has been <strong>{{order_status}}</strong>.</p><p style='color:#444;font-size:15px;line-height:1.6'>If you have any questions, please contact our support team.</p>",
                                    "containerPadding": "20px 30px",
                                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                                    "fontSize": "15px",
                                    "lineHeight": "1.6",
                                    "textAlign": "left"
                                }
                            }],
                            "values": {"backgroundColor": "#ffffff", "padding": "0px", "border": {}, "borderRadius": "0px"}
                        }],
                        "values": {
                            "backgroundColor": "#f4f4f4",
                            "columnsBackgroundColor": "#ffffff",
                            "padding": "20px 0px",
                            "hideDesktop": False
                        }
                    }
                ],
                "headers": [],
                "footers": [],
                "values": {
                    "contentWidth": 600,
                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                    "preheaderText": "Your order {{order_number}} status update",
                    "backgroundColor": "#e9e9e9",
                    "defaultFontSize": "15px"
                }
            },
            "schemaVersion": 16
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Order Cancelled</title></head>
<body style="margin:0;padding:0;background:#e9e9e9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#e9e9e9;padding:20px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:10px;overflow:hidden;max-width:600px;">
      <tr><td style="background:#c0392b;padding:24px 30px;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:700;">CTSPK</h1>
      </td></tr>
      <tr><td style="padding:30px;">
        <h2 style="color:#c0392b;margin:0 0 16px;font-size:20px;">Order {{order_status}}</h2>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Dear <strong>{{customer_name}}</strong>,</p>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Your order <strong>{{order_number}}</strong> has been <strong>{{order_status}}</strong>.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fff5f5;border-radius:8px;border-left:4px solid #c0392b;padding:4px 0;margin:16px 0;">
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Order ID:</strong> #{{order_id}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Order Number:</strong> {{order_number}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Status:</strong> {{order_status}}</td></tr>
        </table>
        <p style="color:#666;font-size:14px;line-height:1.6;margin:12px 0 0;">If you have any questions or believe this is a mistake, please contact our support team immediately.</p>
      </td></tr>
      <tr><td style="background:#f8f9fa;padding:16px 30px;text-align:center;font-size:12px;color:#888;">
        &copy; CTSPK. All rights reserved.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    },

    # ------------------------------------------------------------------ #
    # 9 — Return Request Created
    # ------------------------------------------------------------------ #
    {
        "id": 9,
        "name": "Return Request Created",
        "slug": "return-request-created",
        "subject": "Return Request Submitted for Order {{order_number}}",
        "is_active": True,
        "language": "en",
        "content": {
            "counters": {"u_row": 4, "u_column": 4, "u_content_text": 4},
            "body": {
                "id": "body",
                "rows": [
                    {
                        "id": "r1",
                        "cells": [1],
                        "columns": [{
                            "id": "c1",
                            "contents": [{
                                "id": "t1",
                                "type": "text",
                                "values": {
                                    "text": "<h2 style='color:#e67e22;margin:0 0 12px'>Return Request Submitted</h2><p style='color:#444;font-size:15px;line-height:1.6'>Dear <strong>{{customer_name}}</strong>,</p><p style='color:#444;font-size:15px;line-height:1.6'>Your return request for order <strong>{{order_number}}</strong> has been submitted successfully.</p><p style='color:#444;font-size:15px;line-height:1.6'><strong>Return ID:</strong> #{{return_id}}<br><strong>Refund Amount:</strong> Rs.{{refund_amount}}<br><strong>Reason:</strong> {{reason}}</p><p style='color:#444;font-size:15px;line-height:1.6'>Our team will review your request and update you shortly.</p>",
                                    "containerPadding": "20px 30px",
                                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                                    "fontSize": "15px",
                                    "lineHeight": "1.6",
                                    "textAlign": "left"
                                }
                            }],
                            "values": {"backgroundColor": "#ffffff", "padding": "0px", "border": {}, "borderRadius": "0px"}
                        }],
                        "values": {
                            "backgroundColor": "#f4f4f4",
                            "columnsBackgroundColor": "#ffffff",
                            "padding": "20px 0px",
                            "hideDesktop": False
                        }
                    }
                ],
                "headers": [],
                "footers": [],
                "values": {
                    "contentWidth": 600,
                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                    "preheaderText": "Your return request for order {{order_number}} has been submitted",
                    "backgroundColor": "#e9e9e9",
                    "defaultFontSize": "15px"
                }
            },
            "schemaVersion": 16
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Return Request Created</title></head>
<body style="margin:0;padding:0;background:#e9e9e9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#e9e9e9;padding:20px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:10px;overflow:hidden;max-width:600px;">
      <tr><td style="background:#e67e22;padding:24px 30px;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:700;">CTSPK</h1>
      </td></tr>
      <tr><td style="padding:30px;">
        <h2 style="color:#e67e22;margin:0 0 16px;font-size:20px;">Return Request Submitted</h2>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Dear <strong>{{customer_name}}</strong>,</p>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Your return request for order <strong>{{order_number}}</strong> has been submitted successfully.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fff8f0;border-radius:8px;border-left:4px solid #e67e22;padding:4px 0;margin:16px 0;">
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Return ID:</strong> #{{return_id}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Order Number:</strong> {{order_number}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Refund Amount:</strong> Rs.{{refund_amount}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Reason:</strong> {{reason}}</td></tr>
        </table>
        <p style="color:#666;font-size:14px;line-height:1.6;margin:12px 0 0;">Our team will review your request within 2–3 business days and notify you of the decision.</p>
      </td></tr>
      <tr><td style="background:#f8f9fa;padding:16px 30px;text-align:center;font-size:12px;color:#888;">
        &copy; CTSPK. All rights reserved.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    },

    # ------------------------------------------------------------------ #
    # 10 — Return Request Approved
    # ------------------------------------------------------------------ #
    {
        "id": 10,
        "name": "Return Request Approved",
        "slug": "return-request-approved",
        "subject": "Your Return Request for Order {{order_number}} is Approved",
        "is_active": True,
        "language": "en",
        "content": {
            "counters": {"u_row": 4, "u_column": 4, "u_content_text": 4},
            "body": {
                "id": "body",
                "rows": [
                    {
                        "id": "r1",
                        "cells": [1],
                        "columns": [{
                            "id": "c1",
                            "contents": [{
                                "id": "t1",
                                "type": "text",
                                "values": {
                                    "text": "<h2 style='color:#27ae60;margin:0 0 12px'>Return Approved</h2><p style='color:#444;font-size:15px;line-height:1.6'>Dear <strong>{{customer_name}}</strong>,</p><p style='color:#444;font-size:15px;line-height:1.6'>Great news! Your return request <strong>#{{return_id}}</strong> for order <strong>{{order_number}}</strong> has been <strong>approved</strong>.</p><p style='color:#444;font-size:15px;line-height:1.6'><strong>Refund Amount:</strong> Rs.{{refund_amount}}</p><p style='color:#444;font-size:15px;line-height:1.6'>The refund will be credited to your wallet within 15 business days.</p>",
                                    "containerPadding": "20px 30px",
                                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                                    "fontSize": "15px",
                                    "lineHeight": "1.6",
                                    "textAlign": "left"
                                }
                            }],
                            "values": {"backgroundColor": "#ffffff", "padding": "0px", "border": {}, "borderRadius": "0px"}
                        }],
                        "values": {
                            "backgroundColor": "#f4f4f4",
                            "columnsBackgroundColor": "#ffffff",
                            "padding": "20px 0px",
                            "hideDesktop": False
                        }
                    }
                ],
                "headers": [],
                "footers": [],
                "values": {
                    "contentWidth": 600,
                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                    "preheaderText": "Your return request has been approved",
                    "backgroundColor": "#e9e9e9",
                    "defaultFontSize": "15px"
                }
            },
            "schemaVersion": 16
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Return Approved</title></head>
<body style="margin:0;padding:0;background:#e9e9e9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#e9e9e9;padding:20px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:10px;overflow:hidden;max-width:600px;">
      <tr><td style="background:#27ae60;padding:24px 30px;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:700;">CTSPK</h1>
      </td></tr>
      <tr><td style="padding:30px;">
        <h2 style="color:#27ae60;margin:0 0 16px;font-size:20px;">Return Request Approved</h2>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Dear <strong>{{customer_name}}</strong>,</p>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Your return request has been <strong>approved</strong>.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0faf4;border-radius:8px;border-left:4px solid #27ae60;padding:4px 0;margin:16px 0;">
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Return ID:</strong> #{{return_id}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Order Number:</strong> {{order_number}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Refund Amount:</strong> Rs.{{refund_amount}}</td></tr>
        </table>
        <p style="color:#666;font-size:14px;line-height:1.6;margin:12px 0 0;">The refund will be credited to your wallet. Please allow up to 15 business days for the credit to appear.</p>
      </td></tr>
      <tr><td style="background:#f8f9fa;padding:16px 30px;text-align:center;font-size:12px;color:#888;">
        &copy; CTSPK. All rights reserved.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    },

    # ------------------------------------------------------------------ #
    # 11 — Return Request Rejected
    # ------------------------------------------------------------------ #
    {
        "id": 11,
        "name": "Return Request Rejected",
        "slug": "return-request-rejected",
        "subject": "Your Return Request for Order {{order_number}} was Not Approved",
        "is_active": True,
        "language": "en",
        "content": {
            "counters": {"u_row": 4, "u_column": 4, "u_content_text": 4},
            "body": {
                "id": "body",
                "rows": [
                    {
                        "id": "r1",
                        "cells": [1],
                        "columns": [{
                            "id": "c1",
                            "contents": [{
                                "id": "t1",
                                "type": "text",
                                "values": {
                                    "text": "<h2 style='color:#7f8c8d;margin:0 0 12px'>Return Request Not Approved</h2><p style='color:#444;font-size:15px;line-height:1.6'>Dear <strong>{{customer_name}}</strong>,</p><p style='color:#444;font-size:15px;line-height:1.6'>We regret to inform you that your return request <strong>#{{return_id}}</strong> for order <strong>{{order_number}}</strong> has been <strong>rejected</strong>.</p><p style='color:#444;font-size:15px;line-height:1.6'><strong>Reason:</strong> {{rejected_reason}}</p><p style='color:#444;font-size:15px;line-height:1.6'>If you have any questions, please contact our support team.</p>",
                                    "containerPadding": "20px 30px",
                                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                                    "fontSize": "15px",
                                    "lineHeight": "1.6",
                                    "textAlign": "left"
                                }
                            }],
                            "values": {"backgroundColor": "#ffffff", "padding": "0px", "border": {}, "borderRadius": "0px"}
                        }],
                        "values": {
                            "backgroundColor": "#f4f4f4",
                            "columnsBackgroundColor": "#ffffff",
                            "padding": "20px 0px",
                            "hideDesktop": False
                        }
                    }
                ],
                "headers": [],
                "footers": [],
                "values": {
                    "contentWidth": 600,
                    "fontFamily": {"label": "Arial", "value": "Arial,Helvetica,sans-serif"},
                    "preheaderText": "Update on your return request for order {{order_number}}",
                    "backgroundColor": "#e9e9e9",
                    "defaultFontSize": "15px"
                }
            },
            "schemaVersion": 16
        },
        "html_content": """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Return Rejected</title></head>
<body style="margin:0;padding:0;background:#e9e9e9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#e9e9e9;padding:20px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:10px;overflow:hidden;max-width:600px;">
      <tr><td style="background:#7f8c8d;padding:24px 30px;">
        <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:700;">CTSPK</h1>
      </td></tr>
      <tr><td style="padding:30px;">
        <h2 style="color:#7f8c8d;margin:0 0 16px;font-size:20px;">Return Request Not Approved</h2>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">Dear <strong>{{customer_name}}</strong>,</p>
        <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 12px;">We regret to inform you that your return request for order <strong>{{order_number}}</strong> has been <strong>rejected</strong>.</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f8f9fa;border-radius:8px;border-left:4px solid #7f8c8d;padding:4px 0;margin:16px 0;">
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Return ID:</strong> #{{return_id}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Order Number:</strong> {{order_number}}</td></tr>
          <tr><td style="padding:6px 16px;color:#555;font-size:14px;"><strong>Reason:</strong> {{rejected_reason}}</td></tr>
        </table>
        <p style="color:#666;font-size:14px;line-height:1.6;margin:12px 0 0;">If you believe this decision was made in error, please contact our support team with supporting documents.</p>
      </td></tr>
      <tr><td style="background:#f8f9fa;padding:16px 30px;text-align:center;font-size:12px;color:#888;">
        &copy; CTSPK. All rights reserved.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    },
]


def seed_email_templates(session: Session) -> None:
    """
    Insert email templates 7-11 if they do not already exist.
    Safe to call multiple times — skips existing IDs.
    """
    for tpl in TEMPLATES:
        existing = session.get(Emailtemplate, tpl["id"])
        if existing:
            print(f"[seed] Email template ID {tpl['id']} already exists — skipping.")
            continue

        record = Emailtemplate(
            id=tpl["id"],
            name=tpl["name"],
            slug=tpl["slug"],
            subject=tpl["subject"],
            content=tpl["content"],
            html_content=tpl["html_content"],
            is_active=tpl["is_active"],
            language=tpl["language"],
        )
        session.add(record)
        print(f"[seed] Inserted email template ID {tpl['id']}: {tpl['name']}")

    session.commit()
    print("[seed] Email template seeding complete.")
