import asyncio
import httpx
import random

# Feature 3 (Use two URLs)
RIDE_URL = "http://127.0.0.1:9000/ride_request/"
COURIER_URL = "http://127.0.0.1:9000/courier_request/"

users = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
# --- Feature 3 (Updated: 15 Locations in Bengaluru) ---
locations = [
    "Koramangala", "Indiranagar", "Whitefield", "HSR Layout", "Electronic City",
    "Jayanagar", "JP Nagar", "Malleswaram", "Hebbal", "MG Road",
    "Marathahalli", "Banashankari", "BTM Layout", "Yelahanka", "Majestic"
]
package_sizes = ["Small", "Medium", "Large"]

async def book_job(client, user_name):
    source = random.choice(locations)
    destination = random.choice([loc for loc in locations if loc != source])
    
    # --- Feature 3 (Randomly book ride or package) ---
    if random.choice([True, True, False]): # Book rides 2/3 of the time
        # --- Book a Ride ---
        payload = {
            "user_name": user_name,
            "source": source,
            "destination": destination
        }
        url = RIDE_URL
        job_type = "Ride"
    else:
        # --- Book a Courier Job ---
        payload = {
            "user_name": user_name,
            "source": source,
            "destination": destination,
            "package_size": random.choice(package_sizes)
        }
        url = COURIER_URL
        job_type = "Package"
    
    try:
        response = await client.post(url, json=payload)
        
        if response.status_code == 201:
            price = response.json().get('price', 0)
            print(f"✅ Success ({job_type}): {user_name} booked job #{response.json()['id']} for ₹{price:.2f}")
        else:
            error_detail = response.json().get('detail') if response.content else response.reason_phrase
            print(f"❌ Failed for {user_name} ({job_type}): {response.status_code} - {error_detail}")
    except httpx.ConnectError as e:
        print(f"Connection Error for {user_name}: Could not connect to server.")


async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [book_job(client, user) for user in users]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    print("🚀 Simulating 6 concurrent clients (Rides & Packages) with Bengaluru locations...")
    asyncio.run(main())
    print("Simulation complete.")