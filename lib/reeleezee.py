import os
import logging
import requests
import datetime
import uuid
import pycountry

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

def _get_country_id(country_name):
    try:
        country = pycountry.countries.lookup(country_name)
        return country.alpha_2
    except LookupError:
        logging.warning(f"Could not find country code for: {country_name}")
        return None

def create_customer(customer_id, name, email, address=None):
    payload = {
        "Name": name,
        "SearchName": name,
        "Email": email
    }

    url = f"{BASE_URL}/{ADMIN_ID}/customers/{customer_id}"
    response = requests.put(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        logging.info("Customer created or updated: %s", response.json())

        if address:
            _create_customer_address(customer_id, address)

        return True
    else:
        logging.error("Error creating customer: %s", response.text)
        return False

def _create_customer_address(customer_id, address):
    address_id = str(uuid.uuid4())
    country_id = _get_country_id(address.get("country"))

    if not country_id:
        logging.warning("Skipping address creation due to unknown country.")
        return

    payload = {
        "Street": address.get("street"),
        "Number": address.get("number"),
        "NumberExtension": address.get("number_extension", ""),
        "City": address.get("city"),
        "Postcode": address.get("zipcode"),
        "Country": {
            "id": country_id
        },
        "Type": 2,
        "IsPostal": True
    }

    url = f"{BASE_URL}/{ADMIN_ID}/Customers/{customer_id}/Addresses/{address_id}"
    response = requests.put(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        logging.info("Address added successfully for customer %s", customer_id)
    else:
        logging.error("Failed to add address for customer %s: %s", customer_id, response.text)

def _prepare_invoice_items(booking):
    return [
        {
            "Sequence": idx + 1,
            "Quantity": item["quantity"],
            "Price": round(item["line_price"] / 1.21, 2),
            "LineTotalPayableAmount": item["line_price"],  # price incl. VAT
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

def _generate_reference(booking):
    return "BOOQABLE-" + booking.get("reference", "")

def create_invoice(customer_id, items, reference):
    invoice_id = str(uuid.uuid4())
    payload = {
        "Entity": {"id": customer_id},
        "InvoiceDate": str(datetime.date.today()),
        "DueDate": str(datetime.date.today() + datetime.timedelta(days=30)),
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

# Create and book a sales invoice in Reeleezee.
# This uses manual invoice lines, links to a customer, applies tax and account codes,
# and returns a success/failure result with message and IDs for logging.
def process_booking(booking):
    customer_data = booking["customer"]
    customer_id = customer_data["id"]
    customer_name = customer_data["name"]
    customer_email = customer_data["email"]
    customer_address = customer_data.get("address")
    reference = _generate_reference(booking)

    if not create_customer(customer_id, customer_name, customer_email, customer_address):
        return {
            "success": False,
            "customer_id": customer_id,
            "invoice_id": None,
            "message": f"Failed to create/update customer: {customer_name}"
        }

    items = _prepare_invoice_items(booking)

    invoice_id = create_invoice(customer_id, items, reference)
    if not invoice_id:
        return {
            "success": False,
            "customer_id": customer_id,
            "invoice_id": None,
            "message": f"Failed to create invoice for customer {customer_name}"
        }

    if not book_invoice(invoice_id):
        return {
            "success": False,
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "message": f"Failed to book invoice {invoice_id} for customer {customer_name}"
        }

    return {
        "success": True,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "message": f"Invoice {invoice_id} created and booked for customer {customer_name}"
    }
