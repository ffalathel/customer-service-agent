import hashlib
import hmac
import os


def customer_token(customer_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), customer_id.encode(), hashlib.sha256).hexdigest()


def verify(customer_id: str, token: str, secret: str) -> bool:
    return hmac.compare_digest(customer_token(customer_id, secret), token)


if __name__ == "__main__":
    import sys

    print(customer_token(sys.argv[1], os.environ["RESOLVE_SECRET"]))
