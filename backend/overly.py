import mmap
import struct
import sys
import random
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg
from collections import deque
HISTORY = 400

accPpath = "Local\\acpmf_physics"


fmt_Physics = '<i' + 'f' * 3 + 'ii' + 'f' * 2 + '3f3f' + '4f4f4f4f4f4f4f4f4f' + \
      'fffff' + '5f' + 'iif' + 'fff' + 'if' + '2f' + 'fffff' + '3f' + \
      'ff' + 'iiiii' + 'f' + 'ii' + '4ff' + '4f4f4f' + 'i' + '12f12f12f' + 'f3f'


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


physics_struct = struct.Struct(fmt_Physics)

class Overlay(QtWidgets.QMainWindow):
    physics_struct = struct.Struct(fmt_Physics)
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.Tool
          
        )
        self.graph = pg.PlotWidget(self)
        self.setGeometry(200, 500, 800, 200) 
        #self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
      
        
        self.graph.setMouseEnabled(x=False, y=False)
        self.graph.setMenuEnabled(False)
        self.graph.setGeometry(-30, -10, 830, 199)

        self.graph.setBackground(None)
        
        self.graph.setYRange(0, 1.1 , padding=0)
        self.y = deque([0.0] * HISTORY, maxlen=HISTORY)
        self.x = list(range(HISTORY))

        self.y2 = deque([0.0] * HISTORY, maxlen=HISTORY)
        

        self.y3 = deque([0.5] * HISTORY, maxlen=HISTORY)
        

        self.curve = self.graph.plot(self.x, self.y, pen='g')
        self.curve2 = self.graph.plot(self.x, self.y2, pen='r')
        self.curve3 = self.graph.plot(self.x, self.y3, pen='w')
        self.graph.getAxis('bottom').setStyle(showValues=False)
        self.graph.getAxis('left').setStyle(showValues=False)
        self.graph.setLabel('bottom', None)
        self.graph.setLabel('left', "")

        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(15)
        self._drag_pos = None
        self.graph.showGrid(x=True, y=True, alpha=0.3)
        self.graph.getViewBox().installEventFilter(self)
        self.graph.viewport().installEventFilter(self)
        self.phys_map = mmap.mmap(-1, 584, accPpath, access=mmap.ACCESS_READ)
       

    def eventFilter(self, obj, event):
        watched = {self.graph.getViewBox(), self.graph.viewport()}
        if obj in watched:
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                self._drag_pos = event.globalPosition().toPoint()
                return True
            elif event.type() == QtCore.QEvent.Type.MouseMove:
                if self._drag_pos is not None:
                    delta = event.globalPosition().toPoint() - self._drag_pos
                    self.move(self.pos() + delta)
                    self._drag_pos = event.globalPosition().toPoint()
                return True
            elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                self._drag_pos = None
                return True
        return super().eventFilter(obj, event)
   
    def get_traces(self):
        vals = self.physics_struct.unpack(self.phys_map)
        return vals[1], vals[2], vals[6]

    def update_graph(self):
        traces = self.get_traces()
        self.y.append(traces[0])
        self.curve.setData(self.x, list(self.y))

        self.y2.append(traces[1])
        self.curve2.setData(self.x, list(self.y2))
        
        val = max(-1.0, min(1.0, traces[2]))  
        self.y3.append((val + 1.0) / 2.0)    
   
       
        self.curve3.setData(self.x, list(self.y3))

    

app = QtWidgets.QApplication(sys.argv)
window = Overlay()
window.show()
sys.exit(app.exec()) 