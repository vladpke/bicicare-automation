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

# Retrieve all paid orders and filter those with payments succeeded yesterday
def get_paid_orders():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    url = f'{BOOQABLE_BASE_URL}orders?filter[payment_status]=paid&include=payments'
    response = requests.get(url, headers=booqable_headers)

    if response.status_code == 200:
        data = response.json()
        orders = data.get('data', [])
        included = data.get('included', [])

        def get_payments_for_order(order_id):
            return [item for item in included if item['type'] == 'payments' and item['relationships']['order']['data']['id'] == order_id]

        filtered_orders = []
        for order in orders:
            order_id = order['id']
            payments = get_payments_for_order(order_id)
            for payment in payments:
                succeeded_at = payment['attributes'].get('succeeded_at', '')
                if succeeded_at.startswith(yesterday):
                    filtered_orders.append(order)
                    break

        return filtered_orders

    logging.error(f"Error fetching orders from Booqable: {response.text}")
    return []
