from pydantic import BaseModel
from typing import Optional
# --- Feature 3 (Import new models) ---
from .models import DriverStatus, RideStatus, Location, PoolStatus
import datetime

# Schema for driver login/registration
class DriverCreate(BaseModel):
    name: str

# Simplified ride creation schema
class RideRequestCreate(BaseModel):
    user_name: str
    # --- Feature 3 (Use Enum) ---
    source: Location
    destination: Location

# --- Feature 3 (Courier Schemas) ---
class CourierRequestCreate(BaseModel):
    user_name: str
    source: Location
    destination: Location
    package_size: str

# For displaying a driver
class Driver(BaseModel):
    id: int
    name: str
    status: DriverStatus
    # --- Feature 3 ---
    is_courier: bool
    
    class Config:
        from_attributes = True

# --- Feature 3 (Courier Display Schema) ---
class CourierRequest(BaseModel):
    id: int
    user_name: str
    source: Location
    destination: Location
    package_size: str
    status: RideStatus
    driver: Optional[Driver] = None
    created_at: datetime.datetime
    price: Optional[float] = None

    class Config:
        from_attributes = True

# For displaying a ride request
class RideRequest(BaseModel):
    id: int
    user_name: str
    # --- Feature 3 (Use Enum) ---
    source: Location
    destination: Location
    status: RideStatus
    driver: Optional[Driver] = None
    created_at: datetime.datetime
    price: Optional[float] = None 

    # --- Feature 3 ---
    # This tells the user's browser if a pool is waiting for them
    pool_status: Optional[PoolStatus] = None

    class Config:
        from_attributes = True

# --- Feature 3 (Pooled Trip Schema for Driver) ---
class PooledTrip(BaseModel):
    id: int
    ride: RideRequest
    courier: CourierRequest
    status: PoolStatus
    
    class Config:
        from_attributes = True