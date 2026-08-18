"""
PAYMENT COLLECTION SYSTEM
=========================
Generates payment links (PayPal + Crypto) and tracks payments.

USAGE:
  python3 scripts/payment_system.py generate <lead_name> <email>   # Generate payment link
  python3 scripts/payment_system.py status                          # Show payment status
"""
import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PAYMENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "payments.json")

PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL", "")
CRYPTO_USDT = os.getenv("CRYPTO_USDT_ADDRESS", "")
CRYPTO_BTC = os.getenv("CRYPTO_BTC_ADDRESS", "")
CRYPTO_ETH = os.getenv("CRYPTO_ETH_ADDRESS", "")
CRYPTO_NETWORK = os.getenv("CRYPTO_NETWORK", "BEP20")

SETUP_PRICE = 500
MONTHLY_PRICE = 200


def generate_payment_link(lead_name, email=""):
    """Generate payment links for a lead."""
    paypal_link = f"https://www.paypal.com/paypalme/{PAYPAL_EMAIL.split('@')[0]}/{SETUP_PRICE}" if PAYPAL_EMAIL else ""
    if not paypal_link and PAYPAL_EMAIL:
        paypal_link = f"https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business={PAYPAL_EMAIL}&amount={SETUP_PRICE}&item_name=AI+Voice+Assistant+Setup"

    payment = {
        "lead_name": lead_name,
        "email": email,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "amount": SETUP_PRICE,
        "links": {
            "paypal": paypal_link,
            "crypto_usdt": f"{CRYPTO_USDT}" if CRYPTO_USDT else "",
            "crypto_btc": f"{CRYPTO_BTC}" if CRYPTO_BTC else "",
            "crypto_eth": f"{CRYPTO_ETH}" if CRYPTO_ETH else "",
            "crypto_network": CRYPTO_NETWORK,
        },
        "invoice_id": f"AIPA-{datetime.utcnow().strftime('%Y%m%d')}-{len(get_all_payments())+1:04d}",
    }

    payments = get_all_payments()
    payments.append(payment)
    with open(PAYMENTS_FILE, "w") as f:
        json.dump(payments, f, indent=2)

    return payment


def get_all_payments():
    """Load all payment records."""
    if not os.path.exists(PAYMENTS_FILE):
        return []
    try:
        with open(PAYMENTS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def mark_paid(invoice_id, method="paypal"):
    """Mark a payment as completed."""
    payments = get_all_payments()
    for p in payments:
        if p["invoice_id"] == invoice_id:
            p["status"] = "paid"
            p["paid_at"] = datetime.utcnow().isoformat()
            p["method"] = method
            with open(PAYMENTS_FILE, "w") as f:
                json.dump(payments, f, indent=2)
            return p
    return None


def get_payment_stats():
    """Get summary stats."""
    payments = get_all_payments()
    pending = [p for p in payments if p["status"] == "pending"]
    paid = [p for p in payments if p["status"] == "paid"]
    total_revenue = sum(p["amount"] for p in paid)
    return {
        "total": len(payments),
        "pending": len(pending),
        "paid": len(paid),
        "revenue": total_revenue,
        "pending_amount": sum(p["amount"] for p in pending),
    }


def format_payment_message(payment):
    """Format the payment message to send to leads."""
    links = payment["links"]
    msg = f"""Thank you for choosing AI Pro Assist!

Your Invoice: {payment['invoice_id']}
Amount Due: ${payment['amount']} (one-time setup)

PAY ONLINE — choose any option:

1. PayPal (fastest):
{links['paypal']}

2. Crypto ({links.get('crypto_network', 'BEP20')}):
   USDT: {links.get('crypto_usdt', 'N/A')}
   BTC:  {links.get('crypto_btc', 'N/A')}
   ETH:  {links.get('crypto_eth', 'N/A')}

Once payment is complete, we'll set up your AI voice assistant within 48 hours.

Questions? Reply to this email or call us.
— AI Pro Assist Team"""
    return msg


def main():
    parser = argparse.ArgumentParser(description="Payment Collection System")
    parser.add_argument("command", choices=["generate", "status", "format"], help="What to do")
    parser.add_argument("--name", help="Lead name (for generate)")
    parser.add_argument("--email", default="", help="Lead email (for generate)")
    parser.add_argument("--invoice", help="Invoice ID (for format)")
    args = parser.parse_args()

    if args.command == "generate":
        if not args.name:
            print("ERROR: --name required for generate")
            return
        payment = generate_payment_link(args.name, args.email)
        print(f"✅ Payment generated!")
        print(f"   Invoice: {payment['invoice_id']}")
        print(f"   Amount: ${payment['amount']}")
        print(f"   PayPal: {payment['links']['paypal']}")
        print(f"   USDT: {payment['links'].get('crypto_usdt', 'N/A')}")
        print()
        print("=== MESSAGE TO SEND ===")
        print(format_payment_message(payment))

    elif args.command == "status":
        stats = get_payment_stats()
        print("=== PAYMENT STATUS ===")
        print(f"  Total invoices: {stats['total']}")
        print(f"  Pending: {stats['pending']} (${stats['pending_amount']})")
        print(f"  Paid: {stats['paid']}")
        print(f"  Revenue: ${stats['revenue']}")

    elif args.command == "format":
        payments = get_all_payments()
        for p in payments:
            if not args.invoice or p["invoice_id"] == args.invoice:
                print(format_payment_message(p))
                print("---")


if __name__ == "__main__":
    main()
