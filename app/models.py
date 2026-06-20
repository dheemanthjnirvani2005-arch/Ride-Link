import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, func, Float, Boolean
from sqlalchemy.orm import relationship
from .database import Base

# --- Feature 3 (Location Enum) ---
# Updated: 15 Real Locations in Bengaluru
class Location(str, enum.Enum):
    Koramangala = "Koramangala"
    Indiranagar = "Indiranagar"
    Whitefield = "Whitefield"
    HSR_Layout = "HSR Layout"
    Electronic_City = "Electronic City"
    Jayanagar = "Jayanagar"
    JP_Nagar = "JP Nagar"
    Malleswaram = "Malleswaram"
    Hebbal = "Hebbal"
    MG_Road = "MG Road"
    Marathahalli = "Marathahalli"
    Banashankari = "Banashankari"
    BTM_Layout = "BTM Layout"
    Yelahanka = "Yelahanka"
    Majestic = "Majestic"

class DriverStatus(str, enum.Enum):
    available = "available"
    busy = "busy"
    offline = "offline"

class RideStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    completed = "completed"
    cancelled = "cancelled"
    # --- Feature 3 ---
    # A ride is 'pending_pool' when it's waiting for the *user* to approve
    pending_pool = "pending_pool" 

# --- Feature 3 (Pool Status) ---
class PoolStatus(str, enum.Enum):
    pending_rider = "pending_rider"         # Waiting for User X (rider) to approve
    pending_driver = "pending_driver"     # Waiting for a driver to accept
    active = "active"                   # Driver accepted and is en-route
    completed = "completed"             # Pool is done
    rejected = "rejected"               # User X or Driver rejected

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    status = Column(Enum(DriverStatus), default=DriverStatus.available)
    
    # --- Feature 3 (Courier Opt-in) ---
    is_courier = Column(Boolean, default=False)
    
    rides = relationship("RideRequest", back_populates="driver")
    # --- Feature 3 ---
    courier_jobs = relationship("CourierRequest", back_populates="driver")
    pooled_trips = relationship("PooledTrip", back_populates="driver")

class RideRequest(Base):
    __tablename__ = "ride_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    
    # --- Feature 3 (Use Enum) ---
    source = Column(Enum(Location))
    destination = Column(Enum(Location))
    
    status = Column(Enum(RideStatus), default=RideStatus.pending)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    driver = relationship("Driver", back_populates="rides")

    price = Column(Float, nullable=True)
    
    # --- Feature 3 ---
    # Link to a pool
    pool = relationship("PooledTrip", back_populates="ride", uselist=False)

# --- Feature 3 (Courier Table) ---
class CourierRequest(Base):
    __tablename__ = "courier_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    
    source = Column(Enum(Location))
    destination = Column(Enum(Location))
    
    package_size = Column(String, default="Small") # e.g., Small, Medium, Large
    
    status = Column(Enum(RideStatus), default=RideStatus.pending) # Re-using RideStatus enum
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    driver = relationship("Driver", back_populates="courier_jobs")
    price = Column(Float, nullable=True)
    
    # Link to a pool
    pool = relationship("PooledTrip", back_populates="courier", uselist=False)

# --- Feature 3 (Link Table for Pools) ---
class PooledTrip(Base):
    __tablename__ = "pooled_trips"
    id = Column(Integer, primary_key=True, index=True)
    
    ride_id = Column(Integer, ForeignKey("ride_requests.id"), unique=True)
    courier_id = Column(Integer, ForeignKey("courier_requests.id"), unique=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    
    status = Column(Enum(PoolStatus), default=PoolStatus.pending_rider)
    
    ride = relationship("RideRequest", back_populates="pool")
    courier = relationship("CourierRequest", back_populates="pool")
    driver = relationship("Driver", back_populates="pooled_trips")