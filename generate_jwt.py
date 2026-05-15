import jwt
import time

secret = "super-secret-jwt-token-with-at-least-32-characters-long"

anon_payload = {
    "role": "anon",
    "iss": "supabase",
    "iat": int(time.time()),
    "exp": int(time.time()) + 315360000
}

service_payload = {
    "role": "service_role",
    "iss": "supabase",
    "iat": int(time.time()),
    "exp": int(time.time()) + 315360000
}

anon_key = jwt.encode(anon_payload, secret, algorithm="HS256")
service_key = jwt.encode(service_payload, secret, algorithm="HS256")

print(f"ANON_KEY={anon_key}")
print(f"SERVICE_ROLE_KEY={service_key}")
