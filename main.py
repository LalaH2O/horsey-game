"""
main.py — Entry point for the Horsey Game.
"""

import pygame
from world import run_world


def main() -> None:
    pygame.init()
    run_world()
    pygame.quit()


if __name__ == "__main__":
    main()
