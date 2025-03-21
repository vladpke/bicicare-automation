import os
import requests
import datetime

USERNAME = os.getenv('REELEEZEE_USERNAME')
PASSWORD = os.getenv('REELEEZEE_PASSWORD')
BASE_URL = 'https://apps.reeleezee.nl/api/v1'

HEADERS = {
    'Accept': 'application/json',
    'Accept-Language': 'en',
    'Content-Type': 'application/json; charset=utf-8',
    'Prefer': 'return=representation'
}

def get_auth():
    return requests.auth.HTTPBasicAuth(USERNAME, PASSWORD)

def create_invoice(customer_name, customer_email, items, total_amount):
    payload = {
        "Customer": {
            "Name": customer_name,
            "Email": customer_email
        },
        "InvoiceDate": str(datetime.date.today()),
        "DueDate": str(datetime.date.today() + datetime.timedelta(days=30)),
        "TotalAmount": total_amount,
        "Items": items
    }

    response = requests.post(f'{BASE_URL}/salesinvoices', auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code == 201:
        invoice_id = response.json().get("Id")
        print("Invoice created successfully:", response.json())
        if book_invoice(invoice_id):
            return invoice_id
        else:
            return None
    else:
        print("Error creating invoice:", response.text)
        return None

def book_invoice(invoice_id):
    response = requests.post(f'{BASE_URL}/salesinvoices/{invoice_id}/book', auth=get_auth(), headers=HEADERS)
    if response.status_code == 204:
        print(f"Invoice {invoice_id} booked successfully.")
        return True
    else:
        print(f"Failed to book invoice {invoice_id}:", response.text)
        return False

def create_receipt(customer_name, customer_email, total_amount, invoice_id):
    payload = {
        "Customer": {
            "Name": customer_name,
            "Email": customer_email
        },
        "ReceiptDate": str(datetime.date.today()),
        "TotalAmount": total_amount,
        "Description": "Payment for Bicycle Rental",
        "RelatedInvoiceId": invoice_id
    }

    response = requests.post(f'{BASE_URL}/receipts', auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code == 201:
        print("Receipt created successfully:", response.json())
    else:
        print("Error creating receipt:", response.text)

def process_booking(booking):
    customer_name = booking["customer_name"]
    customer_email = booking["customer_email"]
    items = [{
        "Description": item["description"],
        "Quantity": item["quantity"],
        "UnitPrice": item["unit_price"]
    } for item in booking["items"]]
    total_amount = sum(item["unit_price"] * item["quantity"] for item in booking["items"])

    invoice_id = create_invoice(customer_name, customer_email, items, total_amount)

    if invoice_id:
        create_receipt(customer_name, customer_email, total_amount, invoice_id)
