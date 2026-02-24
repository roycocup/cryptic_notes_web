#!/usr/bin/env python3
"""
CLI script to delete anonymous Firebase Auth users.
Can be run via cron for periodic cleanup.

Usage:
    python cleanup_anon_users.py
    
Cron example (daily at 2 AM):
    0 2 * * * cd /path/to/website && python scripts/cleanup_anon_users.py >> /var/log/cleanup.log 2>&1
"""

import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_admin import auth
from config import firebase_admin


def delete_anonymous_users(next_page_token=None):
    """Recursively delete anonymous users in batches."""
    # List users (max 1000 per batch)
    result = auth.list_users(page_token=next_page_token)

    # Filter for anonymous users (no provider data, no email, no phone)
    to_delete = [
        user.uid
        for user in result.users
        if len(user.provider_data) == 0
        and not user.email
        and not user.phone_number
    ]

    if to_delete:
        print(f"Deleting {len(to_delete)} anonymous users...")
        res = auth.delete_users(to_delete)
        print(f"Success: {res.success_count}, errors: {res.failure_count}")

    # Recursively process next page if available
    if result.next_page_token:
        delete_anonymous_users(result.next_page_token)


def main():
    try:
        delete_anonymous_users()
        print("Finished deleting anonymous users")
        sys.exit(0)
    except Exception as e:
        print(f"Error deleting anonymous users: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
