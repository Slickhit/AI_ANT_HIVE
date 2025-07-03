from ..constants import FOOD_SIZE
from ..sprites import create_glowing_icon


class FoodDrop:
    """Limited food source that disappears after its charges are used."""

    def __init__(self, sim: "AntSim", x: int, y: int, charges: int = 5) -> None:
        self.sim = sim
        self.charges = charges
        self.item = sim.canvas.create_rectangle(
            x,
            y,
            x + FOOD_SIZE,
            y + FOOD_SIZE,
            outline="",
            fill="",
        )

        self.icon = None
        self.flash_icon = None
        self.image_item = None
        self.tooltip = None

        if hasattr(sim.canvas, "create_image"):
            self.icon = create_glowing_icon(FOOD_SIZE)
            self.flash_icon = create_glowing_icon(FOOD_SIZE, inner="#ffffff", outer="#ffcc00")
            self.image_item = sim.canvas.create_image(x, y, image=self.icon, anchor="nw")
            self.tooltip = sim.canvas.create_text(
                x + FOOD_SIZE / 2,
                y - 10,
                text=f"{self.charges} left",
                state="hidden",
                fill="black",
                font=("Arial", 8),
            )
            sim.canvas.tag_bind(self.image_item, "<Enter>", self._show_tooltip)
            sim.canvas.tag_bind(self.image_item, "<Leave>", self._hide_tooltip)
            sim.canvas.tag_bind(self.image_item, "<Button-1>", self._on_click)

    def _show_tooltip(self, _event=None) -> None:
        if self.tooltip is not None:
            self.sim.canvas.itemconfigure(self.tooltip, state="normal")

    def _hide_tooltip(self, _event=None) -> None:
        if self.tooltip is not None:
            self.sim.canvas.itemconfigure(self.tooltip, state="hidden")

    def _flash(self) -> None:
        if self.image_item and self.flash_icon:
            self.sim.canvas.itemconfigure(self.image_item, image=self.flash_icon)
            if hasattr(self.sim, "master") and hasattr(self.sim.master, "after"):
                self.sim.master.after(
                    100, lambda: self.sim.canvas.itemconfigure(self.image_item, image=self.icon)
                )

    def _on_click(self, _event=None) -> None:
        self.take_charge()

    def take_charge(self) -> bool:
        if self.charges <= 0:
            return False
        self.charges -= 1
        self._flash()
        if self.tooltip is not None:
            self.sim.canvas.itemconfigure(self.tooltip, text=f"{self.charges} left")
        if self.charges <= 0:
            self.sim.canvas.delete(self.item)
            if self.image_item:
                self.sim.canvas.delete(self.image_item)
            if self.tooltip:
                self.sim.canvas.delete(self.tooltip)
        return True
