import logging
from lib.booqable import get_paid_orders
from lib.reeleezee import process_booking

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)

def process_all_paid_orders():
    paid_orders = get_paid_orders()

    if not paid_orders:
        logging.info("No paid orders found today.")
        return

    logging.info(f"Processing {len(paid_orders)} paid orders...")

    successes = []
    failures = []

    for order in paid_orders:
        result = process_booking(order)
        if result["success"]:
            successes.append(result)
        else:
            failures.append(result)

    logging.info(f"✅ Successfully processed {len(successes)} orders:")
    for entry in successes:
        logging.info(f"- {entry['message']}")

    if failures:
        logging.warning(f"❌ Failed to process {len(failures)} orders:")
        for entry in failures:
            logging.warning(f"- {entry['message']}")

if __name__ == "__main__":
    process_all_paid_orders()
