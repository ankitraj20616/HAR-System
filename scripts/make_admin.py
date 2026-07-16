import urllib.request
import urllib.error
import json
import sys
import os

def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip("'\"")
    else:
        # Fallback to current directory if script run from root
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            k, v = line.split("=", 1)
                            env[k.strip()] = v.strip().strip("'\"")
    return env

def make_admin(email):
    env = load_env()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key or "placeholder" in key:
        print("Error: Valid SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY missing in .env")
        sys.exit(1)

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    print(f"Looking up user '{email}'...")
    req = urllib.request.Request(f"{url}/auth/v1/admin/users", headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            # Handle Supabase Auth API response differences
            user_list = data.get("users", []) if isinstance(data, dict) else data
            
            user_id = None
            for u in user_list:
                if u.get("email") == email:
                    user_id = u.get("id")
                    break
            
            if not user_id:
                print(f"Error: User '{email}' not found.")
                print("Make sure you have created the account from the dashboard first!")
                sys.exit(1)
                
            print(f"Found user! UUID: {user_id}")
            
            print(f"Updating role to admin...")
            update_req = urllib.request.Request(
                f"{url}/rest/v1/user_roles?user_id=eq.{user_id}",
                data=json.dumps({"role": "admin"}).encode("utf-8"),
                headers=headers,
                method="PATCH"
            )
            with urllib.request.urlopen(update_req) as update_resp:
                if update_resp.status in [200, 204]:
                    print(f"Success! '{email}' is now an admin.")
                    print("Please log out and log in again on your dashboard to get admin access.")
                else:
                    print(f"Failed to update role. HTTP Status: {update_resp.status}")

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/make_admin.py <email>")
        sys.exit(1)
    make_admin(sys.argv[1])
