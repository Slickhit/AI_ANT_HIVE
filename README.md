# AI Ant Hive

AI Ant Hive is a small Tkinter based simulation of an ant colony. Worker ants gather
food and deliver it to their queen while scouts explore the surroundings. The GUI
displays how much food has been collected, how much has been fed to the queen and
the number of active ants.

<!-- Optionally include a screenshot or GIF demonstrating the ants moving and feeding the queen. -->

## Setup

1. Install **Python 3.11** or newer.
2. Install dependencies with `pip install -r requirements.txt`.
3. Environment variables can be loaded from a `.env` file via `python-dotenv`, though none are required for basic usage.
4. Start the GUI using `python ant_sim.py`.

## Running the simulation

Start the GUI with:

```bash
python ant_sim.py
```

### Controls

The sidebar on the right lists each ant's status and overall colony metrics.
At the top of the sidebar you'll find a **Food Drop** button. Clicking it lets
you place additional food sources in the simulation. Just below the button a
small statistics label continuously updates with collected food, how much has
been fed to the queen, the number of active ants, the current egg count and
how many predators are present.

### Day-Night Cycle

The world slowly transitions between day and night over a 60‑second cycle.
A small icon in the top-left corner shows the sun or moon along with the
current day number. Nighttime applies a subtle blue tint without hiding the
scene so the ants remain fully visible. The simulation tracks the day count
via `AntSim.current_day`, which increments every 60 seconds.

## Development

The `tests` folder contains a small test suite. Run it with:

```bash
python -m pytest
```


## License

This project is licensed under the [MIT License](LICENSE).

