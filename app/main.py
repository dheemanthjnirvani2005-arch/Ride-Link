import sys
import os
import random 
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from sqlalchemy import or_
from pydantic import BaseModel

# Ensure we can import from current directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models, schemas
from app.database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- File Serving ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

def get_static_file(filename):
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {filename}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
async def serve_index_page():
    return HTMLResponse(content=get_static_file("index.html"), status_code=200)

@app.get("/driver", response_class=HTMLResponse)
async def serve_driver_page():
    return HTMLResponse(content=get_static_file("driver.html"), status_code=200)

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin_page():
    return HTMLResponse(content=get_static_file("admin.html"), status_code=200)

# --- Logic Helpers ---
# Updated: Logic mapping for Bengaluru locations
def get_location_value(location):
    loc_str = location.value if hasattr(location, 'value') else str(location)
    location_map = {
        "Koramangala": 1, 
        "Indiranagar": 2, 
        "Whitefield": 3, 
        "HSR Layout": 4, 
        "Electronic City": 5,
        "Jayanagar": 6, 
        "JP Nagar": 7, 
        "Malleswaram": 8, 
        "Hebbal": 9, 
        "MG Road": 10,
        "Marathahalli": 11,
        "Banashankari": 12,
        "BTM Layout": 13,
        "Yelahanka": 14,
        "Majestic": 15
    }
    return location_map.get(loc_str, 0)

# --- Dynamic Pool Checker ---
def check_for_pool_opportunity(ride: models.RideRequest, db: Session):
    # Only look for pools if assigned and not already pooled
    if ride.status != models.RideStatus.assigned or ride.pool:
        return

    ride_source_val = get_location_value(ride.source)
    ride_dest_val = get_location_value(ride.destination)

    # Find pending packages
    pending_couriers = db.query(models.CourierRequest).filter(
        models.CourierRequest.status == models.RideStatus.pending,
        models.CourierRequest.pool == None
    ).all()

    for courier in pending_couriers:
        courier_source_val = get_location_value(courier.source)
        courier_dest_val = get_location_value(courier.destination)

        # Logic: If locations are 'close' (value difference <= 3)
        is_pickup_close = abs(ride_source_val - courier_source_val) <= 3
        is_dropoff_close = abs(ride_dest_val - courier_dest_val) <= 3

        if is_pickup_close and is_dropoff_close:
            new_pool = models.PooledTrip(
                ride_id=ride.id,
                courier_id=courier.id,
                driver_id=ride.driver_id,
                status=models.PoolStatus.pending_rider 
            )
            db.add(new_pool)
            db.commit()
            print(f"--- Pool Opportunity Created: Ride {ride.id} + Courier {courier.id} ---")
            return

class ActiveJobResponse(BaseModel):
    job_type: str
    status: str
    details: Union[schemas.RideRequest, schemas.CourierRequest]

@app.get("/active_job/{user_name}", response_model=Optional[ActiveJobResponse])
def get_active_job(user_name: str, db: Session = Depends(get_db)):
    # 1. Check for Active Ride
    ride = db.query(models.RideRequest).filter(
        models.RideRequest.user_name == user_name,
        models.RideRequest.status.notin_([models.RideStatus.completed, models.RideStatus.cancelled])
    ).first()

    if ride:
        # Trigger pool logic
        check_for_pool_opportunity(ride, db)
        db.refresh(ride)
        
        resp_ride = schemas.RideRequest.model_validate(ride)
        if ride.pool:
            resp_ride.pool_status = ride.pool.status
        
        return ActiveJobResponse(job_type="ride", status=ride.status, details=resp_ride)

    # 2. Check for Active Courier
    courier = db.query(models.CourierRequest).filter(
        models.CourierRequest.user_name == user_name,
        models.CourierRequest.status.notin_([models.RideStatus.completed, models.RideStatus.cancelled])
    ).first()

    if courier:
        return ActiveJobResponse(job_type="courier", status=courier.status, details=schemas.CourierRequest.model_validate(courier))

    raise HTTPException(status_code=404, detail="No active job")

@app.get("/ride_status/{user_name}", response_model=schemas.RideRequest)
def get_ride_status(user_name: str, db: Session = Depends(get_db)):
    ride = db.query(models.RideRequest).filter(
        models.RideRequest.user_name == user_name
    ).order_by(models.RideRequest.id.desc()).first()
    
    if not ride:
        raise HTTPException(status_code=404, detail="No active ride")
        
    check_for_pool_opportunity(ride, db)
    db.refresh(ride)
    
    resp = schemas.RideRequest.model_validate(ride)
    if ride.pool:
        resp.pool_status = ride.pool.status
    return resp

# --- Endpoints ---

@app.post("/driver/login", response_model=schemas.Driver)
def login_driver(driver: schemas.DriverCreate, db: Session = Depends(get_db)):
    db_driver = db.query(models.Driver).filter(models.Driver.name == driver.name).first()
    if db_driver: return db_driver
    new_driver = models.Driver(name=driver.name, status="offline")
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    return new_driver

@app.post("/driver/toggle_courier/{driver_id}")
def toggle_courier(driver_id: int, db: Session = Depends(get_db)):
    d = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not d: raise HTTPException(404)
    d.is_courier = not d.is_courier
    db.commit()
    return d

@app.post("/ride_request/", response_model=schemas.RideRequest)
def request_ride(ride: schemas.RideRequestCreate, db: Session = Depends(get_db)):
    if db.query(models.RideRequest).filter(
        models.RideRequest.user_name == ride.user_name,
        models.RideRequest.status.notin_(['completed', 'cancelled'])
    ).first():
        raise HTTPException(400, "You already have an active ride.")

    db_ride = models.RideRequest(**ride.model_dump())
    db_ride.price = round(random.uniform(100, 500), 2) # Updated to logical Rupee range
    db.add(db_ride)
    db.commit()
    db.refresh(db_ride)
    return db_ride

@app.post("/courier_request/", response_model=schemas.CourierRequest)
def request_courier(c: schemas.CourierRequestCreate, db: Session = Depends(get_db)):
    if db.query(models.CourierRequest).filter(
        models.CourierRequest.user_name == c.user_name,
        models.CourierRequest.status.notin_(['completed', 'cancelled'])
    ).first():
        raise HTTPException(400, "You already have an active package.")
        
    db_c = models.CourierRequest(**c.model_dump())
    db_c.price = round(random.uniform(50, 200), 2) # Updated to logical Rupee range
    db.add(db_c)
    db.commit()
    db.refresh(db_c)
    return db_c

@app.post("/accept_ride/{ride_id}", response_model=schemas.RideRequest)
def accept_ride(ride_id: int, driver_id: int, db: Session = Depends(get_db)):
    ride = db.query(models.RideRequest).filter(models.RideRequest.id == ride_id).first()
    driver = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not ride or not driver: raise HTTPException(404)
    
    ride.driver_id = driver_id
    ride.status = models.RideStatus.assigned
    driver.status = models.DriverStatus.busy
    db.commit()
    db.refresh(ride)
    print(f"Driver {driver_id} ACCEPTED Ride {ride_id}")
    return ride

@app.post("/pool/approve/{ride_id}")
def approve_pool(ride_id: int, db: Session = Depends(get_db)):
    pool = db.query(models.PooledTrip).filter(models.PooledTrip.ride_id == ride_id).first()
    if not pool: raise HTTPException(404)
    pool.status = models.PoolStatus.pending_driver
    # Apply Discount
    pool.ride.price = round(pool.ride.price * 0.9, 2)
    pool.courier.price = round(pool.courier.price * 0.9, 2)
    db.commit()
    return pool

@app.post("/driver/accept_pool/{pool_id}")
def driver_accept_pool(pool_id: int, driver_id: Optional[int] = None, db: Session = Depends(get_db)):
    pool = db.query(models.PooledTrip).filter(models.PooledTrip.id == pool_id).first()
    if not pool: raise HTTPException(404, "Pool not found")
    
    # Self-heal driver_id
    if not pool.driver_id and driver_id:
        pool.driver_id = driver_id
        
    if not pool.driver_id: raise HTTPException(400, "Pool has no driver assigned")

    pool.status = models.PoolStatus.active
    pool.courier.driver_id = pool.driver_id
    pool.courier.status = models.RideStatus.assigned
    
    db.commit()
    print(f"Pool {pool_id} ACTIVE for Driver {pool.driver_id}")
    return pool

@app.post("/complete_ride/{ride_id}")
def complete_ride(ride_id: int, db: Session = Depends(get_db)):
    ride = db.query(models.RideRequest).filter(models.RideRequest.id == ride_id).first()
    if not ride: raise HTTPException(404)
    ride.status = models.RideStatus.completed
    driver = ride.driver
    
    if ride.pool:
        if ride.pool.courier.status == models.RideStatus.completed:
            ride.pool.status = models.PoolStatus.completed
            if driver: driver.status = models.DriverStatus.available
    elif driver:
        driver.status = models.DriverStatus.available
        
    db.commit()
    return ride

@app.post("/complete_courier/{courier_id}")
def complete_courier(courier_id: int, db: Session = Depends(get_db)):
    c = db.query(models.CourierRequest).filter(models.CourierRequest.id == courier_id).first()
    if not c: raise HTTPException(404)
    c.status = models.RideStatus.completed
    driver = c.driver
    
    if c.pool:
        if c.pool.ride.status == models.RideStatus.completed:
            c.pool.status = models.PoolStatus.completed
            if driver: driver.status = models.DriverStatus.available
            
    db.commit()
    return c

@app.post("/cancel_ride/{ride_id}")
def cancel_ride(ride_id: int, db: Session = Depends(get_db)):
    ride = db.query(models.RideRequest).filter(models.RideRequest.id == ride_id).first()
    if not ride: raise HTTPException(404)
    if ride.pool: db.delete(ride.pool)
    ride.status = models.RideStatus.cancelled
    if ride.driver: ride.driver.status = models.DriverStatus.available
    db.commit()
    return ride

@app.post("/cancel_courier/{courier_id}")
def cancel_courier(courier_id: int, db: Session = Depends(get_db)):
    c = db.query(models.CourierRequest).filter(models.CourierRequest.id == courier_id).first()
    if not c: raise HTTPException(404)
    if c.pool: db.delete(c.pool)
    c.status = models.RideStatus.cancelled
    if c.driver: c.driver.status = models.DriverStatus.available
    db.commit()
    return c

# --- UPDATED: Fetch All Rides + Pooled Info ---
@app.get("/rides")
def get_rides(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.RideRequest)
    if status:
        query = query.filter(models.RideRequest.status == status)
    
    # Manually serialize to include 'is_pooled' info
    results = []
    for r in query.all():
        r_dict = schemas.RideRequest.model_validate(r).model_dump()
        # Pool is active/completed if driver accepted it
        r_dict['is_pooled'] = r.pool is not None and r.pool.status in [models.PoolStatus.active, models.PoolStatus.completed]
        results.append(r_dict)
    return results

# --- UPDATED: Fetch All Couriers + Pooled Info ---
@app.get("/couriers")
def get_all_couriers(db: Session = Depends(get_db)):
    query = db.query(models.CourierRequest)
    results = []
    for c in query.all():
        c_dict = schemas.CourierRequest.model_validate(c).model_dump()
        c_dict['is_pooled'] = c.pool is not None and c.pool.status in [models.PoolStatus.active, models.PoolStatus.completed]
        results.append(c_dict)
    return results

@app.get("/drivers/")
def get_all_drivers(db: Session = Depends(get_db)):
    return db.query(models.Driver).all()

@app.get("/driver/pool_invites/{driver_id}")
def get_pool_invites(driver_id: int, db: Session = Depends(get_db)):
    return db.query(models.PooledTrip).filter(
        models.PooledTrip.driver_id == driver_id,
        models.PooledTrip.status == models.PoolStatus.pending_driver
    ).all()

@app.get("/my_job/{driver_id}")
def get_driver_job(driver_id: int, db: Session = Depends(get_db)):
    pool = db.query(models.PooledTrip).filter(
        models.PooledTrip.driver_id == driver_id,
        models.PooledTrip.status == models.PoolStatus.active
    ).first()
    if pool:
        print(f"DEBUG: Driver {driver_id} -> Found Pool {pool.id}")
        pool_data = schemas.PooledTrip.model_validate(pool)
        return {"type": "pool", "data": pool_data}
    
    rides = db.query(models.RideRequest).filter(
        models.RideRequest.driver_id == driver_id,
        models.RideRequest.status == models.RideStatus.assigned
    ).all()
    
    if rides:
        print(f"DEBUG: Driver {driver_id} -> Found Ride {rides[0].id}")
        ride_data = schemas.RideRequest.model_validate(rides[0])
        return {"type": "ride", "data": ride_data}
        
    print(f"DEBUG: Driver {driver_id} -> No jobs found")
    return {"type": "none"}

@app.post("/drivers/{driver_id}/status")
def update_status(driver_id: int, status: str, db: Session = Depends(get_db)):
    d = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    d.status = status
    db.commit()
    return d