import tkinter as tk
from tkinter import font

class AntHiveUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ant Hive Simulation v0.1")
        width = 800
        height = 600
        self.resizable(False, False)
        left_w = int(width * 0.75)
        right_w = width - left_w
        # Left canvas
        self.canvas = tk.Canvas(self, width=left_w, height=height, bg="#d9c38a")
        self.canvas.pack(side="left", fill="both")
        self.draw_static_elements()
        # Sidebar
        sidebar = tk.Frame(self, width=right_w, height=height, bg="#f7e6cb")
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)
        self.build_sidebar(sidebar)

    def draw_static_elements(self):
        c = self.canvas
        w = int(c["width"])
        h = int(c["height"])
        # cross hatch pattern
        step = 20
        for i in range(0, w, step):
            c.create_line(i, 0, i + h, h, fill="#e0d2a0", width=1)
            c.create_line(i, 0, i - h, h, fill="#e0d2a0", width=1)
        # tunnels
        tunnel_color = "#5d3a1a"
        tunnels = [
            (100, 500, 140, 560),
            (140, 540, 240, 560),
            (240, 540, 240, 440),
            (240, 440, 300, 440),
        ]
        for x1, y1, x2, y2 in tunnels:
            c.create_rectangle(x1, y1, x2, y2, fill=tunnel_color, outline="")
        # obstacles
        for coords in [(60, 60, 100, 80), (200, 200, 240, 240), (320, 120, 360, 160)]:
            c.create_rectangle(*coords, fill="#808080", outline="")
        # queen
        c.create_oval(350, 560, 390, 580, fill="purple", outline="black")
        # food
        c.create_rectangle(20, 20, 28, 28, fill="green", outline="")
        # ants
        ants = [
            ("red", 260, 460),
            ("black", 180, 520),
            ("green", 300, 480),
            ("blue", 220, 440),
        ]
        for color, x, y in ants:
            c.create_rectangle(x, y, x + 8, y + 8, fill=color, outline="")

    def build_sidebar(self, parent):
        # Top section
        top = tk.Frame(parent, bg="#f7e6cb")
        top.pack(side="top", fill="x", pady=10)
        btn = tk.Button(top, text="Food Drop", bg="orange", relief="flat")
        btn.pack(pady=5)
        stats_text = (
            "Food Collected: 1\n"
            "Fed to Queen: 0\n"
            "Ants Active: 5\n"
            "Eggs: 0\n"
            "Predators: 1"
        )
        tk.Label(top, text=stats_text, bg="#f7e6cb", anchor="w", justify="left").pack(fill="x")
        # Middle section
        mid = tk.Frame(parent, bg="#f7e6cb")
        mid.pack(side="top", fill="x", pady=10)
        tk.Label(mid, text="Ant Stats:", bg="#f7e6cb").pack(anchor="w")
        for i in range(5):
            row = tk.Frame(mid, bg="#f7e6cb")
            row.pack(anchor="w")
            icon = tk.Canvas(row, width=10, height=10, bg="#f7e6cb", highlightthickness=0)
            icon.create_rectangle(2, 2, 8, 8, fill="orange", outline="")
            icon.pack(side="left")
            tk.Label(
                row,
                text=f"ID {630+i} | WorkerAnt | E:{4+i%5} | Active",
                bg="#f7e6cb",
            ).pack(side="left")
        # Bottom section
        bottom = tk.Frame(parent, bg="#f7e6cb")
        bottom.pack(side="top", fill="x", pady=10)
        tk.Label(bottom, text="Colony Stats:", bg="#f7e6cb").pack(anchor="w")
        stats = (
            "Food: 1\n"
            "Queen Hunger: 56\n"
            "Ants: 5\n"
            "Eggs: 0"
        )
        tk.Label(bottom, text=stats, bg="#f7e6cb", anchor="w", justify="left").pack(fill="x")
        tk.Label(bottom, text="Queen Thought: This colony better prosper.", bg="#f7e6cb", anchor="w", justify="left").pack(fill="x", pady=(5,0))

if __name__ == "__main__":
    app = AntHiveUI()
    app.mainloop()
