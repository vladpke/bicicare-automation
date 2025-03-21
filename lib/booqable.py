import os
import logging
import requests
import datetime

BOOQABLE_API_KEY = os.getenv('BOOQABLE_API_KEY')
BOOQABLE_BASE_URL = 'https://bicicare.booqable.com/api/boomerang/'

booqable_headers = {
    'Authorization': f'Bearer {BOOQABLE_API_KEY}',
    'Content-Type': 'application/json'
}

# Fetch the succeeded_at timestamp from payments of a given order (if any)
def get_payment_for_order(order_id):
    url = f'{BOOQABLE_BASE_URL}orders/{order_id}/payments'
    response = requests.get(url, headers=booqable_headers)

    if response.status_code == 200:
        payments = response.json().get('data', [])
        for payment in payments:
            succeeded_at = payment['attributes'].get('succeeded_at')
            if succeeded_at:
                return succeeded_at
    logging.error(f"Error fetching payment for order {order_id}: {response.text}")
    return None

def get_paid_orders():
    url = f'{BOOQABLE_BASE_URL}orders?filter[payment_status]=paid'
    response = requests.get(url, headers=booqable_headers)

    if response.status_code == 200:
        orders = response.json().get('data', [])
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        return [order for order in orders if get_payment_for_order(order['id']).startswith(yesterday)]

    logging.error(f"Error fetching orders from Booqable: {response.text}")
    return []

# Convert a Booqable order into the format expected for Reeleezee invoicing
def transform_order_to_booking(order):
    customer_name = order['attributes']['customer_name']
    customer_email = order['attributes']['customer_email']

    items = []
    for item in order['relationships']['order_items']['data']:
        item_detail = item['attributes']
        items.append({
            "description": item_detail['name'],
            "quantity": item_detail['quantity'],
            "unit_price": float(item_detail['price'])
        })

    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items
    }