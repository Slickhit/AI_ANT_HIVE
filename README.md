# AI Ant Hive

AI Ant Hive is a small Tkinter based simulation of an ant colony. Worker ants gather food and feed it to their queen while scout ants wander the area. A simple dashboard displays how much food has been collected, how much has been fed to the queen and how many ants are currently active.

## Queen Behavior

The queen is now an active entity with a hunger meter and a spawn timer.

- **Hunger** slowly decreases over time and is replenished when worker ants
  deliver food. When hunger drops below 50, the queen turns red as a visual
  signal that she needs more food.
- **Spawning** occurs automatically when the spawn timer reaches zero. A new
  worker ant is created near the queen and the timer resets.

<!-- Optionally include a screenshot or GIF demonstrating the ants moving and feeding the queen. -->
