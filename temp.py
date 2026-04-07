
import time
import h5py
from backend.backend import Backend
from backend.backend import setup
import numpy as np
import datetime


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
                    with h5py.File(setup.set_laps_dir() / f"lap_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.h5", "w") as f:
                        f.create_dataset("throttle", data=np.array(y_value, dtype=np.float32), compression="gzip", compression_opts=4)
                        f.create_dataset("time", data=np.array(x_value, dtype=np.float32), compression="gzip", compression_opts=4)
                        break

