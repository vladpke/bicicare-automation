import os
import logging
import requests
import datetime
import pycountry

# Reeleezee credentials from environment
USERNAME = os.getenv("REELEEZEE_USERNAME")
PASSWORD = os.getenv("REELEEZEE_PASSWORD")
ADMIN_ID = os.getenv("REELEEZEE_ADMIN_ID")
BASE_URL = "https://apps.reeleezee.nl/api/v1"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-NL",
    "Content-Type": "application/json; charset=utf-8",
    "Prefer": "return=representation",
    "x-client": "A202509.2.3",
    "x-serialization-options": "preserve-references-implicit"
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

def create_customer(name, email, address=None):
    payload = {
        "Name": name,
        "SearchName": name,
        "CommunicationChannelList": [
            {
                "CommunicationType": 10,
                "FormattedValue": email
            }
        ],
        "EntityType": {
            "id": "83b1d717-a669-4687-ace0-4de08ee58f93"
        }
    }

    url = f"{BASE_URL}/{ADMIN_ID}/Customers"
    response = requests.post(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        customer = response.json()
        customer_id = customer.get("id")
        logging.info("Customer created successfully: %s", customer_id)

        if address:
            _create_customer_address(customer_id, address)

        return customer_id
    else:
        logging.error("Error creating customer: %s", response.text)
        return None

def _create_customer_address(customer_id, address):
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

    url = f"{BASE_URL}/{ADMIN_ID}/Customers/{customer_id}/Addresses"
    response = requests.post(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        logging.info("Address added successfully for customer %s", customer_id)
    else:
        logging.error("Failed to add address for customer %s: %s", customer_id, response.text)

def _generate_header(booking):
    return "Booqable-" + booking.get("booqable_order_number", "")

def _create_invoice_shell(customer_id, header):
    payload = {
        "Entity": {"id": customer_id},
        "DocumentType": 10,
        "Origin": 2,
        "Type": 1,
        "InvoiceDate": str(datetime.date.today()),
        "DueDate": str(datetime.date.today() + datetime.timedelta(days=30)),
        "Header": header
    }

    url = f"{BASE_URL}/{ADMIN_ID}/SalesInvoices"
    response = requests.post(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        invoice = response.json()
        invoice_id = invoice.get("id")
        logging.info("Invoice shell created: %s", invoice_id)
        return invoice_id
    else:
        logging.error("Error creating invoice shell: %s", response.text)
        return None

def _add_invoice_lines_placeholder(invoice_id, count):
    lines = [{"Sequence": i + 1, "Quantity": 1} for i in range(count)]

    payload = {
        "id": invoice_id,
        "DocumentType": 10,
        "Type": 1,
        "Origin": 2,
        "DocumentLineList": lines
    }

    url = f"{BASE_URL}/{ADMIN_ID}/SalesInvoices/{invoice_id}?$expand=DocumentLineList"
    response = requests.put(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        document = response.json()
        line_ids = [line["id"] for line in document.get("DocumentLineList", [])]
        logging.info("Line placeholders added: %s", line_ids)
        return line_ids
    else:
        logging.error("Failed to add invoice lines: %s", response.text)
        return []

def _update_invoice_lines(invoice_id, line_ids, booking_items):
    updated_lines = []

    for idx, (line_id, item) in enumerate(zip(line_ids, booking_items)):
        updated_lines.append({
            "id": line_id,
            "Sequence": idx + 1,
            "Quantity": item["quantity"],
            "Price": round(item["line_price"] / 1.21, 2),
            "Description": item["description"],
            "DocumentCategoryAccount": {
                "id": "61f4ae1b-7700-4685-9930-ddfe71fb626e"
            },
            "TaxRate": {"id": "1e44993a-15f6-419f-87e5-3e31ac3d9383"}
        })

    payload = {
        "id": invoice_id,
        "DocumentLineList": updated_lines
    }

    url = f"{BASE_URL}/{ADMIN_ID}/SalesInvoices/{invoice_id}"
    response = requests.put(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        logging.info("Invoice lines updated for invoice %s", invoice_id)
        return True
    else:
        logging.error("Failed to update invoice lines: %s", response.text)
        return False

def book_invoice(invoice_id):
    url = f"{BASE_URL}/{ADMIN_ID}/SalesInvoices/{invoice_id}/Actions"
    payload = {"id": invoice_id, "Type": 17}
    response = requests.post(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code == 204:
        logging.info("Invoice booked successfully: %s", invoice_id)
        return True
    else:
        logging.error("Error booking invoice %s: %s", invoice_id, response.text)
        return False

# Step-by-step orchestration of the Reeleezee sales invoice creation and booking
def process_booking(booking):
    customer_data = booking["customer"]
    customer_name = customer_data["name"]
    customer_email = customer_data["email"]
    customer_address = customer_data.get("address")
    header = _generate_header(booking)

    customer_id = create_customer(customer_name, customer_email, customer_address)
    if not customer_id:
        return {
            "success": False,
            "customer_id": None,
            "invoice_id": None,
            "message": f"Failed to create customer: {customer_name}"
        }

    invoice_id = _create_invoice_shell(customer_id, header)
    if not invoice_id:
        return {
            "success": False,
            "customer_id": customer_id,
            "invoice_id": None,
            "message": f"Failed to create invoice shell for {customer_name}"
        }

    line_ids = _add_invoice_lines_placeholder(invoice_id, len(booking["items"]))
    if not line_ids:
        return {
            "success": False,
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "message": f"Failed to add lines to invoice {invoice_id}"
        }

    if not _update_invoice_lines(invoice_id, line_ids, booking["items"]):
        return {
            "success": False,
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "message": f"Failed to update lines for invoice {invoice_id}"
        }

    if not book_invoice(invoice_id):
        return {
            "success": False,
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "message": f"Failed to book invoice {invoice_id}"
        }

    return {
        "success": True,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "message": f"Invoice {invoice_id} created and booked for customer {customer_name}"
    }
