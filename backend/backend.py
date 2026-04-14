import atexit
import datetime
import mmap
import os
import struct
import sqlite3
from pathlib import Path
import uuid
import numpy as np
import h5py
from fastapi import FastAPI, HTTPException
import threading
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

accSpath = "Local\\acpmf_static"
accPpath = "Local\\acpmf_physics"
accGpath = "Local\\acpmf_graphics"
fmt_static = '<' + '30s30s' + 'ii' + '66s' * 5 + '2x' + \
      'i' + 'ffif' + '4f' + '4f' + 'fff' + 'i' + 'fffff' + 'ii' + \
      'iii' + 'f' + 'ii' + 'f' + '66s' + '2x' + \
      'f' + 'ii' + '66s' + '2x' + \
      'iiii' + '66s66s'

fmt_Physics = '<i' + 'f' * 3 + 'ii' + 'f' * 2 + '3f3f' + '4f4f4f4f4f4f4f4f4f' + \
      'fffff' + '5f' + 'iif' + 'fff' + 'if' + '2f' + 'fffff' + '3f' + \
      'ff' + 'iiiii' + 'f' + 'ii' + '4ff' + '4f4f4f' + 'i' + '12f12f12f' + 'f3f'

fmt_Graphics = (
    '<'
    'i i i'
    '30s 30s 30s 30s'
    'i i i i i'
    'f f'
    'i i i i i'
    '66s'
    'f f'
    'i'
    + 'f' * (60 * 3)
    + 'i' * 60 +
    'i'
    'f'
    'i i'
    'i i'
    'f'
    'i'
    'f f'
    'i i i'
    'i i i i'
    'f'
    'i i i'
    'f'
    'i'
    'i i'
    'i i'
    'f'
    '30s'
    'i'
    '30s'
    'i'
    'i i i'
    'f'
    '66s'
    'i'
    'f'
    'i i'
    'i i i i i i i i i i'
    'i f f f f f'
    'i i i i'
    'i i'
    'i i'
)

fields_Graphics = [
    "packetId", "status", "session",
    "currentTime", "lastTime", "bestTime", "split",
    "completedLaps", "position", "iCurrentTime", "iLastTime", "iBestTime",
    "sessionTimeLeft", "distanceTraveled", "isInPit", "currentSectorIndex", 
    "lastSectorTime", "numberOfLaps", "tyreCompound", "replayTimeMultiplier",
    "normalizedCarPosition", "activeCars",
    *[f"carCoordinates_{i}_{a}" for i in range(60) for a in "xyz"],
    *[f"carID_{i}" for i in range(60)],
    "playerCarID", "penaltyTime", "flag", "penalty", "idealLineOn", 
    "isInPitLane", "surfaceGrip", "mandatoryPitDone", "windSpeed", "windDirection",
    "isSetupMenuVisible", "mainDisplayIndex", "secondaryDisplayIndex", 
    "TC", "TCCUT", "EngineMap", "ABS", "fuelXLap", "rainLights", "flashingLights", 
    "lightsStage", "exhaustTemperature", "wiperLV", "driverStintTotalTimeLeft", 
    "driverStintTimeLeft", "rainTyres", "sessionIndex", "usedFuel",
    "deltaLapTime", "estimatedLapTime", # These are wide strings
    "iDeltaLapTime", "iEstimatedLapTime", "isDeltaPositive", "iSplit", "isValidLap",
    "fuelEstimatedLaps", "trackStatus", "missingMandatoryPits", "Clock",
    "directionLightsLeft", "directionLightsRight", "GlobalYellow", "GlobalYellow1",
    "GlobalYellow2", "GlobalYellow3", "GlobalWhite", "GlobalGreen", 
    "GlobalChequered", "GlobalRed", "mfdTyreSet", "mfdFuelToAdd",
    "mfdTyrePressureLF", "mfdTyrePressureRF", "mfdTyrePressureLR", "mfdTyrePressureRR",
    "trackGripStatus", "rainIntensity", "rainIntensityIn10min", 
    "rainIntensityIn30min", "currentTyreSet", "strategyTyreSet", "gapAhead", "gapBehind"
]

fields_Static = [
    "smVersion", "acVersion",
    "numberOfSessions", "numCars",
    "carModel", "track", "playerName", "playerSurname", "playerNick",
    "sectorCount", "maxTorque", "maxPower", "maxRpm", "maxFuel",
    *[f"suspMaxTravel_{w}" for w in ("fl", "fr", "rl", "rr")],
    *[f"tyreRadius_{w}" for w in ("fl", "fr", "rl", "rr")],
    "maxTurboBoost", "deprecated_1", "deprecated_2", "penaltiesEnabled",
    "aidFuelRate", "aidTireRate", "aidMechanicalDamage", "AllowTyreBlankets", "aidStability",
    "aidAutoclutch", "aidAutoBlip",
    "hasDRS", "hasERS", "hasKERS", "kersMaxJ",
    "engineBrakeSettingsCount", "ersPowerControllerCount",
    "trackSplineLength", "trackConfiguration", 
    "ersMaxJ", "isTimedRace", "hasExtraLap", "carSkin",
    "reversedGridPositions", "PitWindowStart", "PitWindowEnd", "isOnline",
    "dryTyresName", "wetTyresName"
]

fields_Physics = [
    "packetId","gas","brake","fuel","gear","rpms","steerAngle","speedKmh",
    "vel_x","vel_y","vel_z","accG_x","accG_y","accG_z",
    "slip_fl","slip_fr","slip_rl","slip_rr",
    "load_fl","load_fr","load_rl","load_rr",
    "psi_fl","psi_fr","psi_rl","psi_rr",
    "wspd_fl","wspd_fr","wspd_rl","wspd_rr",
    "wear_fl","wear_fr","wear_rl","wear_rr",
    "dirt_fl","dirt_fr","dirt_rl","dirt_rr",
    "tcoreT_fl","tcoreT_fr","tcoreT_rl","tcoreT_rr",
    "camber_fl","camber_fr","camber_rl","camber_rr",
    "susp_fl","susp_fr","susp_rl","susp_rr",
    "drs","tc","heading","pitch","roll","cgHeight",
    "dmg_f","dmg_r","dmg_l","dmg_ri","dmg_c",
    "tyresOut","pitLimiter","abs",
    "kersCharge","kersInput","autoShifter",
    "rideH_f","rideH_r",
    "turbo","ballast","airDensity","airTemp","roadTemp",
    "angVel_x","angVel_y","angVel_z",
    "finalFF","perfMeter",
    "engineBrake","ersRecovery","ersPower","ersHeatCharge","ersCharging",
    "kersKJ","drsAvail","drsEnabled",
    "brakeT_fl","brakeT_fr","brakeT_rl","brakeT_rr","clutch",
    "tTempI_fl","tTempI_fr","tTempI_rl","tTempI_rr",
    "tTempM_fl","tTempM_fr","tTempM_rl","tTempM_rr",
    "tTempO_fl","tTempO_fr","tTempO_rl","tTempO_rr",
    "isAI",
    *[f"tcp_{w}_{a}" for w in ("fl","fr","rl","rr") for a in "xyz"],
    *[f"tcn_{w}_{a}" for w in ("fl","fr","rl","rr") for a in "xyz"],
    *[f"tch_{w}_{a}" for w in ("fl","fr","rl","rr") for a in "xyz"],
    "brakeBias","lvel_x","lvel_y","lvel_z",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend = Backend()
    handler = HandleTraces(backend, hz=100)
    

    telemetry_thread = threading.Thread(target=handler.loop, daemon=True)
    telemetry_thread.start()
    
    yield 


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


class Backend:
    physics_struct = struct.Struct(fmt_Physics)
    static_struct = struct.Struct(fmt_static)
    graphic_struct = struct.Struct(fmt_Graphics)


    def __init__(self):
        self.phys_map = mmap.mmap(-1, 584, accPpath, access=mmap.ACCESS_READ)
        self.graph_map = mmap.mmap(-1, struct.calcsize(fmt_Graphics), accGpath, access=mmap.ACCESS_READ)
        self.static_map = mmap.mmap(-1, 820, accSpath, access=mmap.ACCESS_READ)
        try:
            self.conn = sqlite3.connect('database.db', check_same_thread=False)
            self.db = self.conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise
        self.db_init()
        atexit.register(self.exit)

    def db_init(self):
        try:
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS laps (
                    UUID TEXT PRIMARY KEY,
                    lap_time TEXT,
                    car TEXT,
                    track TEXT,
                    tel_path TEXT,
                    date_time TEXT,
                    favorite INTEGER DEFAULT 0
                )
            ''')
            self.conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise

    def exit(self):
        self.phys_map.close()
        self.graph_map.close()
        self.conn.commit()
        self.conn.close()
        
    def get_traces(self):
        vals = self.physics_struct.unpack(self.phys_map)
        return vals[1], vals[2], vals[6]
    
    def get_distance(self):
        vals = self.graphic_struct.unpack(self.graph_map)
        
        return vals[fields_Graphics.index("normalizedCarPosition")]
    
    def get_laps(self):
        vals = self.graphic_struct.unpack(self.graph_map)
        laps = vals[fields_Graphics.index("completedLaps")]
        
        
        last_time_bytes = vals[fields_Graphics.index("lastTime")]
        formatted_time = last_time_bytes.decode('utf-16-le').rstrip('\x00')
        
        return laps, formatted_time
    
    
    def get_track(self):     
        vals = self.static_struct.unpack(self.static_map)
        track_name = vals[fields_Static.index("track")]
        return track_name.decode('utf-16-le').rstrip('\x00')
    
   
    def get_car(self):
        vals = self.static_struct.unpack(self.static_map)
        car_name = vals[fields_Static.index("carModel")]
        return car_name.decode('utf-16-le').rstrip('\x00')

class setup:
    @staticmethod
    def set_laps_dir(folder_type: str):
    
        if os.name == 'nt':
            base_path = Path(os.environ.get('LOCALAPPDATA', ''))
        else:
            base_path = Path.cwd() 
            
        
        if folder_type == "default":
            lap_dir = base_path / "OpenSimTelemetry" / "laps"
        else:
            lap_dir = base_path / "OpenSimTelemetry" / "laps" / folder_type
            
        lap_dir.mkdir(parents=True, exist_ok=True)
        return lap_dir


class HandleTraces:
    def __init__(self, backend, hz=70):
        self.backend = backend
        self.interval = 1.0 / hz   
       
        self.x_dist = []
        self.y_gas = []
        self.y_brake = []
        self.y_steering = []
        self.samples = []


        self.last_lap, _ = backend.get_laps()

    def loop(self):
        print("Telemetry loop started.")
        while True:
            

            gas, brake, steering = self.backend.get_traces()
            x = self.backend.get_distance()
            

            self.samples.append({
            "gas": gas,
            "brake": brake,
            "steering": steering,
            "normalized_pos": x,
            })
            
            current_lap, lap_time_string = self.backend.get_laps()

            if current_lap > self.last_lap:
                print(f"Lap {current_lap} completed")
                
                
                try:
                    self.save(lap_time_string)
                    print(f"Successfully saved Lap {current_lap} ({lap_time_string})")
                except Exception as e:
                    print(f"CRITICAL ERROR SAVING LAP: {e}")
                
                self.last_lap = current_lap
                
               
                self.y_gas = []
                self.y_brake = []
                self.y_steering = []
                self.x_dist = []
                

        
                

    def save(self, lap_time_string):
        def write(data, UUID):
           
            filepath = setup.set_laps_dir("default") / f"lap_{UUID}.h5"
            with h5py.File(filepath, "w") as f:
                f.create_dataset("telemtry", data=data, compression="gzip", compression_opts=4)
                
        unique_uuid = str(uuid.uuid4())
        formatted_samples = [
            (s["gas"], s["brake"], s["steering"], s["normalized_pos"]) 
            for s in self.samples
        ]
        data = np.array(formatted_samples, dtype=[
        ("gas", "f4"),
        ("brake", "f4"),
        ("steering", "f4"),
        ("normalized_pos", "f4"),
        ], )
        write(data, unique_uuid)
        
        self.backend.db.execute('''
            INSERT INTO laps (UUID, lap_time, car, track, tel_path, date_time)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (unique_uuid, lap_time_string, self.backend.get_car(), self.backend.get_track(),
             str(setup.set_laps_dir("default")), datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')))
        self.backend.conn.commit()

def main():
    backend = Backend()
    handler = HandleTraces(backend, hz=100)
    handler.loop()


backend = Backend()
@app.get("/laps")
def get_track():
    backend.db.execute("SELECT * FROM laps ORDER BY date_time DESC")
    rows = backend.db.fetchmany(10)
    return [{"uuid":r[0],"lap_time":r[1],"car":r[2],"track":r[3],"tel_path":r[4],"date_time":r[5],"favorite":bool(r[6])} for r in rows]
    
@app.get("/laps/{uuid}/telemetry")
def get_gas(uuid: str) -> dict[str, list]: 
    filepath = setup.set_laps_dir("default") / f"lap_{uuid}.h5"
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Telemetry file not found")

    
    with h5py.File(filepath, "r") as f:
       
        if "telemtry" not in f:
            raise HTTPException(status_code=404, detail="Dataset not found in file")
            
        data = f["telemtry"][:]
        clean_gas = np.round(np.nan_to_num(data["gas"], nan=0.0, posinf=0.0, neginf=0.0), decimals=2).tolist()
        clean_brake = np.round(np.nan_to_num(data["brake"], nan=0.0, posinf=0.0, neginf=0.0), decimals=2).tolist()
        clean_steering = np.round(np.nan_to_num(data["steering"], nan=0.0, posinf=0.0, neginf=0.0), decimals=2).tolist()
        clean_pos = np.round(np.nan_to_num(data["normalized_pos"], nan=0.0, posinf=0.0, neginf=0.0), decimals=2).tolist()

        return {
            "gas": clean_gas,
            "brake": clean_brake,
            "steering": clean_steering,
            "normalized_pos": clean_pos
        }
