import sys
import random
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg
import backend.backend as backend
from collections import deque
HISTORY = 400

class Overlay(QtWidgets.QMainWindow):
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
   

    def update_graph(self):
        traces = backend.get_traces()
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