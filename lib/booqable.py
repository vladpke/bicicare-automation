import os
import logging
import requests
import datetime
import re
from dotenv import load_dotenv

load_dotenv()

BOOQABLE_API_KEY = os.getenv("BOOQABLE_API_KEY")
BOOQABLE_BASE_URL = "https://bicicare.booqable.com/api/boomerang/"

booqable_headers = {
    "Authorization": f"Bearer {BOOQABLE_API_KEY}",
    "Content-Type": "application/json",
}

# Fetch full order details with customer, address and line info
def get_order_details(order_id):
    url = f"{BOOQABLE_BASE_URL}orders/{order_id}?include=payments,lines,customer,customer.properties"
    response = requests.get(url, headers=booqable_headers)

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error fetching order details for {order_id}: {response.text}")
        return None

# Helper function to split address1 into street, number, and number extension
def split_street_and_number(address_line):
    if not address_line:
        return "", "", ""

    match = re.match(r"^(.*?)(?:\s+)?(\d+)([a-zA-Z\-]*)$", address_line.strip())
    if match:
        street = match.group(1).strip()
        number = match.group(2).strip()
        extension = match.group(3).strip()
    else:
        street = address_line.strip()
        number = ""
        extension = ""

    return street, number, extension

# Convert a Booqable order into the format expected for Reeleezee invoicing
def transform_order_to_booking(order, included_lookup):
    customer_id = order["relationships"]["customer"]["data"]["id"]
    customer = included_lookup.get(customer_id, {})
    customer_attributes = customer.get("attributes", {})

    # Look up property (address) info
    address = {}
    property_relationships = customer.get("relationships", {}).get("properties", {}).get("data", [])
    if property_relationships:
        first_property_id = property_relationships[0]["id"]
        property_obj = included_lookup.get(first_property_id, {})
        address_attributes = property_obj.get("attributes", {})

        street, number, extension = split_street_and_number(address_attributes.get("address1", ""))

        address = {
            "street": street,
            "number": number,
            "number_extension": extension,
            "zipcode": address_attributes.get("zipcode"),
            "city": address_attributes.get("city"),
            "country": address_attributes.get("country"),
        }

    customer_data = {
        "name": customer_attributes.get("name"),
        "email": customer_attributes.get("email"),
        "address": address,
    }

    # Extract order lines from included
    line_ids = [line_ref["id"] for line_ref in order.get("relationships", {}).get("lines", {}).get("data", [])]
    lines = []
    for line_id in line_ids:
        line = included_lookup.get(line_id)
        if line and line["type"] == "lines":
            attrs = line.get("attributes", {})
            lines.append({
                "description": attrs.get("title", "Product"),
                "quantity": attrs.get("quantity", 1),
                "line_price": attrs.get("price_in_cents", 0) / 100  # already includes quantity and VAT
            })

    return {
        "booqable_order_number": order.get("attributes", {})["number"],
        "customer": customer_data,
        "lines": lines
    }

# Retrieve paid orders from Booqable that were created yesterday.
# For each order, fetches full details including payments, customer, address, and order lines.
# Filters for orders that have at least one payment succeeded yesterday.
# Transforms each valid order into a booking object compatible with Reeleezee integration,
# including itemized lines and customer address details.
# Returns a list of formatted booking dictionaries ready for invoicing.
def get_paid_orders():
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    start = f"{yesterday}T00:00:00+00:00"
    end = f"{yesterday}T23:59:59+00:00"

    url = (
        f"{BOOQABLE_BASE_URL}orders?"
        f"filter[payment_status]=paid&"
        f"filter[created_at][gte]={start}&"
        f"filter[created_at][lte]={end}&"
        f"include=payments"
    )
    response = requests.get(url, headers=booqable_headers)

    if response.status_code == 200:
        data = response.json()
        orders = data.get("data", [])
        included = data.get("included", [])

        def get_payments_for_order(order_id):
            return [
                item for item in included
                if item["type"] == "payments"
                and item["relationships"].get("order", {}).get("data", {}).get("id") == order_id
            ]

        bookings = []
        for order in orders:
            order_id = order["id"]
            payments = get_payments_for_order(order_id)
            for payment in payments:
                succeeded_at = payment["attributes"].get("succeeded_at", "")
                if succeeded_at.startswith(str(yesterday)):
                    full_order_response = get_order_details(order_id)
                    if full_order_response:
                        full_order = full_order_response.get("data")
                        full_included = full_order_response.get("included", [])
                        included_lookup = {item["id"]: item for item in full_included if "id" in item}
                        bookings.append(transform_order_to_booking(full_order, included_lookup))
                    break

        return bookings

    logging.error(f"Error fetching orders from Booqable: {response.text}")
    return []
