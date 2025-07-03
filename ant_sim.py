import tkinter as tk
import random

# Constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
ANT_SIZE = 10
FOOD_SIZE = 8
MOVE_STEP = 5

class BaseAnt:
    """Base class for all ants."""
    def __init__(self, sim, x, y, color="black"):
        self.sim = sim
        self.item = sim.canvas.create_oval(x, y, x + ANT_SIZE, y + ANT_SIZE, fill=color)
        self.carrying_food = False
        self.last_pos = (x, y)

    def move_random(self):
        dx = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        dy = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        self.sim.canvas.move(self.item, dx, dy)

    def move_towards(self, target):
        x1, y1, _, _ = self.sim.canvas.coords(self.item)
        tx1, ty1, _, _ = self.sim.canvas.coords(target)
        dx = MOVE_STEP if x1 < tx1 else -MOVE_STEP if x1 > tx1 else 0
        dy = MOVE_STEP if y1 < ty1 else -MOVE_STEP if y1 > ty1 else 0
        self.sim.canvas.move(self.item, dx, dy)

    def update(self):
        self.move_random()
        self.last_pos = tuple(self.sim.canvas.coords(self.item)[:2])

class WorkerAnt(BaseAnt):
    """Ant focused on collecting food and feeding the queen."""
    def update(self):
        if not self.carrying_food:
            self.move_towards(self.sim.food)
            if self.sim.check_collision(self.item, self.sim.food):
                self.carrying_food = True
                self.sim.food_collected += 1
                self.sim.move_food()
        else:
            self.move_towards(self.sim.queen)
            if self.sim.check_collision(self.item, self.sim.queen):
                self.sim.queen_fed += 1
                self.carrying_food = False
        self.last_pos = tuple(self.sim.canvas.coords(self.item)[:2])

class ScoutAnt(BaseAnt):
    """Ant that explores randomly, remembering its last position."""
    pass

class AntSim:
    def __init__(self, master):
        self.master = master
        self.canvas = tk.Canvas(master, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg='white')
        self.canvas.pack()

        # Entities
        self.food = self.canvas.create_rectangle(180, 20, 180 + FOOD_SIZE, 20 + FOOD_SIZE, fill='green')
        self.queen = self.canvas.create_oval(180, 570, 180 + 40, 570 + 20, fill='purple')

        # Ants
        self.ants = [WorkerAnt(self, 195, 295, "blue"),
                     WorkerAnt(self, 215, 295, "red"),
                     ScoutAnt(self, 235, 295, "black")]

        # Stats
        self.food_collected = 0
        self.queen_fed = 0
        self.stats_text = self.canvas.create_text(5, 5, anchor='nw', fill='blue', font=('Arial', 10))

        # Kick off loop
        self.update()

    def move_food(self):
        self.canvas.move(self.food, random.randint(-50, 50), random.randint(20, 40))

    def get_coords(self, item):
        return self.canvas.coords(item)

    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def get_stats(self):
        return f"Food Collected: {self.food_collected}\nFed to Queen: {self.queen_fed}\nAnts Active: {len(self.ants)}"

    def update(self):
        for ant in self.ants:
            ant.update()

        self.canvas.itemconfigure(self.stats_text, text=self.get_stats())
        self.master.after(100, self.update)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("AI Ant Hive")
    app = AntSim(root)
    root.mainloop()
