
import atexit
import datetime
import mmap
import os
import struct
import time
import sqlite3
from pathlib import Path
import uuid
import numpy as np
import h5py
from fastapi import FastAPI

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

fmt_Graphics = '<' + \
    'i' + 'i' + 'i' + \
    '30s' * 4 + \
    'i' + 'i' + 'iii' + 'f' + 'f' + 'i' + 'i' + 'i' + 'i' + \
    '66s' + 'f' + 'f' + 'i' + \
    'f' * 180 + 'i' * 60 + 'i' + 'f' + 'i' + 'i' + 'i' + 'i' + 'f' + 'i' + 'f' + 'f' + 'i' + \
    'ii' + 'iiiii' + 'f' + 'ii' + 'i' + 'f' + 'ii' + '66s' * 2 + 'i' * 10 + 'f' * 4 + \
    'iiiii' + 'i' + 'i' + 'iii'

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

app = FastAPI()

class API:
    
    def __init__ (self):
        backend = Backend()
    
    @app.get("/laps")
    def get_track(self):
        backend.db.execute("SELECT * FROM laps ORDER BY date_time DESC")
        rows = backend.db.fetchmany(10)
        return [{"uuid":r[0],"lap_time":r[1],"car":r[2],"track":r[3],"tel_path":r[4],"date_time":r[5],"favorite":bool(r[6]) }, 
        for r in rows]
    
    @app.get("/laps/{uuid}/gas_tel")
    def get_gas(uuid: str):
        backend.db.execute("SELECT tel_path FROM laps WHERE UUID = ?", (uuid,))
        row = backend.db.fetchone()
        if not row:
            raise
        gas_path = Path(row[0])
        gas_path = gas_path / "gas"
        print(gas_path)q


class Backend:
    physics_struct = struct.Struct(fmt_Physics)
    static_struct = struct.Struct(fmt_static)
    graphic_struct = struct.Struct(fmt_Graphics)


    def __init__(self):
        self.phys_map = mmap.mmap(-1, 584, accPpath, access=mmap.ACCESS_READ)
        self.graph_map = mmap.mmap(-1, 1542, accGpath, access=mmap.ACCESS_READ)
        self.static_map = mmap.mmap(-1, 820, accSpath, access=mmap.ACCESS_READ)
        try:
            self.conn = sqlite3.connect('database.db')
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

    def get_laps(self):
        vals = self.graphic_struct.unpack(self.graph_map)
        return vals[fields_Graphics.index("completedLaps")]
    
    
    def get_track(self):     
        vals = self.static_struct.unpack(self.static_map)
        track_name = vals[fields_Static.index("track")]
        return track_name.decode('utf-16-le').rstrip('\x00')
    
   
    def get_car(self):
        vals = self.static_struct.unpack(self.static_map)
        car_name = vals[fields_Static.index("carModel")]
        return car_name.decode('utf-16-le').rstrip('\x00')

class setup:
    def set_laps_dir(type: str):
        if os.name == 'nt':
            base_path = Path(os.environ.get('LOCALAPPDATA'))
        if type == "default":
            return base_path / "OpenSimTelemetry" / "laps"
        lap_dir = base_path / "opentelemetry" / "laps" / type
        lap_dir.mkdir(parents=True, exist_ok=True)
        return lap_dir

class HandleTraces:
    def __init__(self, backend, hz=100):
        self.backend = backend

        self.interval = 1.0 / hz   # 100Hz = 0.01, 200Hz = 0.005
        self.start_time = time.perf_counter()

        self.x_time = []
        self.y_gas = []
        self.y_brake = []
        self.y_steering = []

        self.last_lap = backend.get_laps()

    def loop(self):
        next_tick = time.perf_counter()

        while True:
            gas, brake, steering = self.backend.get_traces()

            now = time.perf_counter()

            self.y_gas.append(gas)
            self.y_brake.append(brake)
            self.y_steering.append(steering)
            self.x_time.append(now - self.start_time)

            current_lap = self.backend.get_laps()
            if current_lap > self.last_lap:
                self.last_lap = current_lap
                self.save()
            
            next_tick += self.interval
            sleep_time = next_tick - time.perf_counter()

            if sleep_time > 0:
                time.sleep(sleep_time)

    def save(self):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')

        def write(name, data):
            with h5py.File(setup.set_laps_dir(name) / f"lap_{timestamp}.h5", "w") as f:
                f.create_dataset(name, data=np.array(data, dtype=np.float32))
                f.create_dataset("time", data=np.array(self.x_time, dtype=np.float32))

        write("gas", self.y_gas)
        write("brake", self.y_brake)
        write("steering", self.y_steering)

        
        self.backend.db.execute('''
            INSERT INTO laps (UUID, lap_time, car, track, tel_path, date_time)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (str(uuid.uuid4()), str(self.x_time[-1]), self.backend.get_car(), self.backend.get_track(),
             str(setup.set_laps_dir("default")), datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')))
        self.backend.conn.commit()

def main():
    backend = Backend()
    handler = HandleTraces(backend, hz=100)
    handler.loop()

main()
