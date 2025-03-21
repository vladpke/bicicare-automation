from lib.booqable import get_paid_orders, transform_order_to_booking
from lib.reeleezee import process_booking

def process_all_paid_orders():
    paid_orders = get_paid_orders()

    if not paid_orders:
        print("No paid orders found today.")
        return

    print(f"Processing {len(paid_orders)} paid orders...")

    for order in paid_orders:
        booking = transform_order_to_booking(order)
        process_booking(booking)

if __name__ == '__main__':
    process_all_paid_orders()
