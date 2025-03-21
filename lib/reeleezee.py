import os
import logging
import requests
import datetime
import uuid


# Reeleezee credentials from environment
USERNAME = os.getenv("REELEEZEE_USERNAME")
PASSWORD = os.getenv("REELEEZEE_PASSWORD")
ADMIN_ID = os.getenv("REELEEZEE_ADMIN_ID")
BASE_URL = "https://apps.reeleezee.nl/api/v1"

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en",
    "Content-Type": "application/json; charset=utf-8",
    "Prefer": "return=representation",
}


def get_auth():
    return requests.auth.HTTPBasicAuth(USERNAME, PASSWORD)


def create_customer(customer_id, name, email):
    payload = {"Name": name, "SearchName": name, "Email": email}

    url = f"{BASE_URL}/{ADMIN_ID}/customers/{customer_id}"
    response = requests.put(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        logging.info("Customer created or updated: %s", response.json())
        return customer_id
    else:
        logging.error("Error creating customer: %s", response.text)
        return None


def create_invoice(customer_id, items, total_amount, reference):
    invoice_id = str(uuid.uuid4())
    payload = {
        "Entity": {"id": customer_id},
        "InvoiceDate": str(datetime.date.today()),
        "DueDate": str(datetime.date.today() + datetime.timedelta(days=30)),
        "TotalAmount": total_amount,
        "Reference": reference,
        "DocumentLineList": items,
    }

    url = f"{BASE_URL}/{ADMIN_ID}/salesinvoices/{invoice_id}"
    response = requests.put(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        logging.info("Invoice created successfully: %s", response.json())
        return invoice_id
    else:
        logging.error("Error creating invoice: %s", response.text)
        return None


def book_invoice(invoice_id):
    url = f"{BASE_URL}/{ADMIN_ID}/salesinvoices/{invoice_id}/Actions"
    payload = {"id": invoice_id, "Type": 17}
    response = requests.post(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code == 204:
        logging.info("Invoice booked successfully: %s", invoice_id)
        return True
    else:
        logging.error("Error booking invoice %s: %s", invoice_id, response.text)
        return False


# Create and book a sales invoice using manual invoice lines and proper tax/account links
def process_booking(booking):
    customer_data = booking["customer"]
    customer_id = customer_data["id"]
    customer_name = customer_data["name"]
    customer_email = customer_data["email"]

    reference = "BOOQABLE-" + booking.get("reference", "")

    # Ensure customer exists in Reeleezee
    created_customer_id = create_customer(customer_id, customer_name, customer_email)
    if not created_customer_id:
        return

    items = [
        {
            "Sequence": idx + 1,
            "Quantity": item["quantity"],
            "Price": item["unit_price"],
            "Description": item["description"],
            "InvoiceLineType": 12,
            "DocumentCategoryAccount": {
                "id": "47e2b087-330a-437d-91b8-706e309efd74",
                "Name": "Omzet 3",
            },
            "TaxRate": {"id": "1e44993a-15f6-419f-87e5-3e31ac3d9383"},
        }
        for idx, item in enumerate(booking["items"])
    ]

    total_amount = sum(
        item["unit_price"] * item["quantity"] for item in booking["items"]
    )

    invoice_id = create_invoice(customer_id, items, total_amount, reference)

    if invoice_id:
        book_invoice(invoice_id)
