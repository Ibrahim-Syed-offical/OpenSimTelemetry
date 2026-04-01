import mmap
import struct

accbpath = "Local\\acpmf_physics"

try: 
    shm = mmap.mmap(-1,0,accbpath,access=mmap.ACCESS_READ)
    shm.seek(0)
    unpack = struct.unpack('<ifffiif', shm.read(28))
    packetid = unpack[0]
    gas = unpack[1]
    brake = unpack[2]
    steering = unpack[6]
    print(f"Gas Pedal: {gas}")
    print(f"Brake Pedal: {brake}")
    print(f"Steering Ang: {steering}")
    
except FileNotFoundError:
    print("File not Found")
    shm.close()