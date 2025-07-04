import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import ANT_SPRITES


def test_ant_sprites_frame_count():
    assert len(ANT_SPRITES) == 4
