
import datetime
import mmap
import os
import struct
import time
import sqlite3
from pathlib import Path
import numpy as np
import h5py

conn = sqlite3.connect('data.db')

db = conn.cursor()
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

fields_static = [
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

class Backend:
    physics_struct = struct.Struct(fmt_Physics)
    static_struct = struct.Struct(fmt_static)
    graphic_struct = struct.Struct(fmt_Graphics)

    @staticmethod
    def get_shm(path, byte_size, field_type, struct_obj):
        with mmap.mmap(-1, byte_size, path, access=mmap.ACCESS_READ) as shm:
            vals = struct_obj.unpack(shm)
        return dict(zip(field_type, vals))
    
    @staticmethod
    def get_traces():
        unpack = Backend.get_shm(accPpath, 584, fields_Physics, Backend.physics_struct)
        gas = unpack["gas"]
        brake = unpack["brake"]
        steering = unpack["steerAngle"]
        return [gas,brake,steering]
    
    @staticmethod
    def get_track():
        unpack = Backend.get_shm(accSpath, 1168, fields_static, Backend.static_struct)
        track_name = unpack["track"]
        return track_name.decode('utf-16-le').rstrip('\x00')
    
    @staticmethod
    def get_laps():
        unpack = Backend.get_shm(accGpath, 1542, fields_Graphics, Backend.graphic_struct)
        lap = unpack["completedLaps"]
        return lap
    
    @staticmethod
    def get_car():
        unpack = Backend.get_shm(accSpath, 1168, fields_static, Backend.static_struct)
        car_name = unpack["carModel"]
        return car_name.decode('utf-16-le').rstrip('\x00')


class setup:
    def set_laps_dir():
        if os.name == 'nt':
            base_path = Path(os.environ.get('LOCALAPPDATA'))
        lap_dir = base_path / "opentelemetry" / "laps"
        lap_dir.mkdir(parents=True, exist_ok=True)
        return lap_dir

class handle_traces:
    def __init__(self):
        self.interval = 0.01

    def dump_throttle(interval=0.01):
            y_value = []
            x_value = []
            current_lap = Backend.get_laps()
            current_time = time.perf_counter()
            start_time = current_time
            while True:
                y_value.append(Backend.get_traces()[0])    
                x_value.append(round(current_time - start_time, 3))
                current_time += interval
                if (Backend.get_laps() - current_lap) > 0:
                    with h5py.File(setup.set_laps_dir() / f"lap_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.h5", "w") as f:
                        f.create_dataset("throttle", data=np.array(y_value))
                        f.create_dataset("time", data=np.array(x_value))