import tkinter as tk
from .sim import AntSim

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Ant Hive Simulation v0.1")
    app = AntSim(root)
    root.mainloop()
