import tkinter as tk
import random

# Constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
ANT_SIZE = 10
FOOD_SIZE = 8
MOVE_STEP = 5

class AntSim:
    def __init__(self, master):
        self.master = master
        self.canvas = tk.Canvas(master, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg='white')
        self.canvas.pack()

        # Entities
        self.ant = self.canvas.create_oval(195, 295, 195 + ANT_SIZE, 295 + ANT_SIZE, fill='black')
        self.food = self.canvas.create_rectangle(180, 20, 180 + FOOD_SIZE, 20 + FOOD_SIZE, fill='green')
        self.queen = self.canvas.create_oval(180, 570, 180 + 40, 570 + 20, fill='purple')

        # Stats
        self.food_collected = 0
        self.queen_fed = 0

        # Kick off loop
        self.update()

    def move_ant(self):
        dx = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        dy = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        self.canvas.move(self.ant, dx, dy)

    def get_coords(self, item):
        return self.canvas.coords(item)

    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def update(self):
        self.move_ant()

        if self.check_collision(self.ant, self.food):
            self.food_collected += 1
            self.canvas.move(self.food, random.randint(-50, 50), 0)

        if self.check_collision(self.ant, self.queen) and self.food_collected > 0:
            fed = int(self.food_collected * 0.9)
            self.queen_fed += fed
            self.food_collected = int(self.food_collected * 0.1)

        self.master.after(100, self.update)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("AI Ant Hive")
    app = AntSim(root)
    root.mainloop()
