import os
import requests
import datetime

BOOQABLE_API_KEY = os.getenv('BOOQABLE_API_KEY')
BOOQABLE_BASE_URL = 'https://bicicare.booqable.com/api/boomerang/'

booqable_headers = {
    'Authorization': f'Bearer {BOOQABLE_API_KEY}',
    'Content-Type': 'application/json'
}

def get_payment_for_order(order_id):
    response = requests.get(f'{BOOQABLE_BASE_URL}orders/{order_id}/payments', headers=booqable_headers)

    if response.status_code == 200:
        payments = response.json().get('data', [])
        for payment in payments:
            succeeded_at = payment['attributes'].get('succeeded_at')
            if succeeded_at:
                return succeeded_at
    else:
        print(f"Error fetching payment for order {order_id}:", response.text)

    return None

def get_paid_orders():
    response = requests.get(f'{BOOQABLE_BASE_URL}orders?filter[payment_status]=paid', headers=booqable_headers)

    if response.status_code == 200:
        orders = response.json().get('data', [])
        today = datetime.date.today().isoformat()
        return [order for order in orders if get_payment_for_order(order['id']).startswith(today)]
    else:
        print("Error fetching orders from Booqable:", response.text)
        return []

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
