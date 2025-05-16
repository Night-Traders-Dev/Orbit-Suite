from core.userutil import load_users, save_users

def view_security_circle(username):
    users = load_users()
    circle = users[username].get("security_circle", [])
    if not circle:
        print("Your Security Circle is empty.")
    else:
        print("Your Security Circle:")
        for user in circle:
            print(f" - {user}")

def add_to_security_circle(username):
    users = load_users()
    new_trust = input("Enter username to add to Security Circle: ").strip()
    if new_trust not in users:
        print("User does not exist.")
        return
    if new_trust == username:
        print("You cannot add yourself.")
        return
    if new_trust in users[username].get("security_circle", []):
        print("User already in your Security Circle.")
        return

    users[username]["security_circle"].append(new_trust)
    save_users(users)
    print(f"{new_trust} added to your Security Circle.")

def remove_from_security_circle(username):
    users = load_users()
    circle = users[username].get("security_circle", [])
    if not circle:
        print("Your Security Circle is already empty.")
        return

    remove_user = input("Enter username to remove: ").strip()
    if remove_user not in circle:
        print("User is not in your Security Circle.")
        return

    users[username]["security_circle"].remove(remove_user)
    save_users(users)
    print(f"{remove_user} removed from your Security Circle.")
