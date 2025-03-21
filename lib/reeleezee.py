import os
import logging
import requests
import datetime
import uuid

# Reeleezee credentials from environment
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

def create_invoice(customer_name, customer_email, items, total_amount, reference):
    invoice_id = str(uuid.uuid4())
    payload = {
        "Customer": {
            "Name": customer_name,
            "Email": customer_email
        },
        "InvoiceDate": str(datetime.date.today()),
        "DueDate": str(datetime.date.today() + datetime.timedelta(days=30)),
        "TotalAmount": total_amount,
        "Reference": reference,
        "Items": items
    }

    url = f'{BASE_URL}/salesinvoices/{invoice_id}'
    response = requests.put(url, auth=get_auth(), headers=HEADERS, json=payload)

    if response.status_code in [200, 201]:
        logging.info('Invoice created successfully: %s', response.json())
        return invoice_id
    else:
        logging.error('Error creating invoice: %s', response.text)
        return None

def book_invoice(invoice_id):
    url = f'{BASE_URL}/salesinvoices/{invoice_id}/book'
    response = requests.post(url, auth=get_auth(), headers=HEADERS)

    if response.status_code == 204:
        logging.info('Invoice booked successfully: %s', invoice_id)
        return True
    else:
        logging.error('Error booking invoice %s: %s', invoice_id, response.text)
        return False

# Create and book a sales invoice with linked ledger account (Omzet 3)
def process_booking(booking):
    customer_name = booking['customer_name']
    customer_email = booking['customer_email']
    reference = 'BOOQABLE-' + booking.get('reference', '')

    items = [
        {
            "Description": item['description'],
            "Quantity": item['quantity'],
            "UnitPrice": item['unit_price'],
            "LedgerAccountId": "47e2b087-330a-437d-91b8-706e309efd74"  # Omzet 3
        }
        for item in booking['items']
    ]

    total_amount = sum(
        item['unit_price'] * item['quantity'] for item in booking['items']
    )

    invoice_id = create_invoice(customer_name, customer_email, items, total_amount, reference)

    if invoice_id:
        book_invoice(invoice_id)
