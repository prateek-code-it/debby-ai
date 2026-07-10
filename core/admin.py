"""
DEBBY! -- core/admin.py
Phase 8.5: the ONLY place users can be added or deleted. brain.py can
only log people into accounts that already exist -- it has no ability
to create or remove them. Run this file directly, separate from the
normal chat flow.

First run ever (no users in the database yet): bootstraps the first
admin account, no login required (someone has to be able to get in).
Every run after that requires logging in as an existing admin first.
"""

import sys
import getpass
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from memory.memory_helper import (  # noqa: E402
    create_user, delete_user, list_users, verify_login, is_admin, user_exists,
)


def bootstrap_first_admin():
    print("=== No users exist yet. Let's create the first admin account. ===")
    user_id = input("Choose a username: ").strip().lower().replace(" ", "_")
    display_name = input("Display name: ").strip() or user_id
    pin = getpass.getpass("Choose a PIN: ").strip()
    confirm = getpass.getpass("Confirm PIN: ").strip()
    if pin != confirm:
        print("PINs didn't match. Try again.")
        return bootstrap_first_admin()
    create_user(user_id, display_name, pin, is_admin=True)
    print(f"Admin account '{user_id}' created.\n")


def admin_login() -> str:
    for attempt in range(3):
        user_id = input("Admin username: ").strip().lower().replace(" ", "_")
        pin = getpass.getpass("Admin PIN: ").strip()
        if verify_login(user_id, pin) and is_admin(user_id):
            return user_id
        print(f"Login failed. ({2 - attempt} attempts left)\n")
    print("Too many failed attempts. Exiting.")
    sys.exit(1)


def add_user():
    user_id = input("New username: ").strip().lower().replace(" ", "_")
    if user_exists(user_id):
        print(f"'{user_id}' already exists.")
        return
    display_name = input("Display name: ").strip() or user_id
    pin = getpass.getpass("Set PIN for this user: ").strip()
    make_admin = input("Make this user an admin too? (y/N): ").strip().lower() == "y"
    create_user(user_id, display_name, pin, is_admin=make_admin)
    print(f"User '{user_id}' created.")


def remove_user():
    users = list_users()
    if not users:
        print("No users exist.")
        return
    print("\nExisting users:")
    for u in users:
        tag = " (admin)" if u["is_admin"] else ""
        print(f"  - {u['user_id']}{tag}")
    target = input("\nUsername to delete: ").strip().lower().replace(" ", "_")
    if not user_exists(target):
        print(f"'{target}' doesn't exist.")
        return
    confirm = input(f"Really delete '{target}'? This removes their history too. (y/N): ").strip().lower()
    if confirm == "y":
        delete_user(target)
        print(f"'{target}' deleted.")
    else:
        print("Cancelled.")


def show_users():
    users = list_users()
    if not users:
        print("No users yet.")
        return
    print("\nCurrent users:")
    for u in users:
        tag = " (admin)" if u["is_admin"] else ""
        print(f"  - {u['user_id']} / {u['display_name']}{tag}")


def main():
    if not list_users():
        bootstrap_first_admin()

    print("=== DEBBY! Admin ===")
    admin_login()
    print("Logged in as admin.\n")

    while True:
        print("\n1) List users\n2) Add user\n3) Delete user\n4) Exit")
        choice = input("> ").strip()
        if choice == "1":
            show_users()
        elif choice == "2":
            add_user()
        elif choice == "3":
            remove_user()
        elif choice == "4":
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
