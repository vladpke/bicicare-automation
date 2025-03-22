import logging
from lib.booqable import get_paid_orders
from lib.reeleezee import process_booking

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)

def process_all_paid_orders():
    paid_bookings = get_paid_orders()

    if not paid_bookings:
        logging.info("No paid orders found today.")
        return

    logging.info(f"Processing {len(paid_bookings)} paid orders...")

    for booking in paid_bookings:
        process_booking(booking)

if __name__ == "__main__":
    process_all_paid_orders()
