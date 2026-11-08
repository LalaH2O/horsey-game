"""
world.py — Overworld map game loop.

Responsible for:
  - Spawning and managing wandering WorldHorse objects
  - Player movement (Player class)
  - Lasso mechanic (Lasso class)
  - Van inventory UI (Van class)
  - Camera management
  - Triggering the race track via run_track()

All constants, drawing helpers and classes are imported from their
dedicated modules.
"""

import random

import pygame

import constants as C
from classes import WorldHorse, Lasso, Van, Player
from methods import (
    get_font,
    build_race_track_sprite,
    build_horse_sprite,
    roll_world_horse_traits,
    draw_grass,
    draw_race_track,
    draw_world_characters,
    update_camera,
    screen_to_world,
)
from track import run_track


# ============================================================
# WORLD ENTRY POINT
# ============================================================

def run_world() -> None:
    """Run the overworld loop until the player quits."""

    # --- Screen setup ---
    screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT))
    pygame.display.set_caption("Horse Racing World")
    clock  = pygame.time.Clock()

    # --- Static world decorations (seeded for reproducibility) ---
    random.seed(12)

    grass_details = [
        (
            random.randint(0, C.WORLD_WIDTH),
            random.randint(0, C.WORLD_HEIGHT),
            random.choice([C.DARK_GRASS, C.LIGHT_GRASS, C.GRASS]),
        )
        for _ in range(900)
    ]

    flowers = [
        (
            random.randint(0, C.WORLD_WIDTH),
            random.randint(0, C.WORLD_HEIGHT),
            random.choice([(255,225,130), (245,170,180), (230,230,245)]),
        )
        for _ in range(100)
    ]

    random.seed()   # back to random seed for gameplay

    # --- Build static sprites (once) ---
    track_sprite = build_race_track_sprite()
    track_rect   = pygame.Rect(660, 280, 620, 460)
    horse_obstacles = [track_rect.inflate(80, 80)]

    # --- Game objects ---
    player = Player(x=300.0, y=450.0)
    lasso  = Lasso()
    van    = Van()

    # Spawn world horses
    horses: list[WorldHorse] = []
    for _ in range(C.HORSE_COUNT):
        traits       = roll_world_horse_traits()
        sprite_right = build_horse_sprite(traits)
        sprite_left  = pygame.transform.flip(sprite_right, True, False)

        h = WorldHorse(traits, sprite_right, sprite_left,
                       x=float(C.WORLD_WIDTH // 2),
                       y=float(C.WORLD_HEIGHT - 80))

        # Find a valid spawn position
        for _ in range(200):
            test_x = random.randint(80, C.WORLD_WIDTH  - 80)
            test_y = random.randint(150, C.WORLD_HEIGHT - 20)
            if not h.can_stand(test_x, test_y, horse_obstacles):
                continue
            if (test_x - player.x) ** 2 + (test_y - player.y) ** 2 < 400 ** 2:
                continue
            h.x = float(test_x)
            h.y = float(test_y)
            break

        horses.append(h)

    # --- Camera ---
    camera_x, camera_y = update_camera(player.x, player.y)

    # --- Fonts ---
    font       = get_font(24, bold=True)
    small_font = get_font(17)
    title_font = get_font(30, bold=True)

    running = True

    while running:
        clock.tick(C.FPS_WORLD)
        mouse_pos = pygame.mouse.get_pos()

        # --------------------------------------------------------
        # EVENTS
        # --------------------------------------------------------
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if van.open:
                        van.toggle()
                    else:
                        running = False

                if event.key == pygame.K_e and player.near_track(track_rect) and not van.open:
                    run_track()
                    # Restore world display after the race
                    screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT))
                    pygame.display.set_caption("Horse Racing World")
                    clock  = pygame.time.Clock()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Van button (top-right)
                button_rect = pygame.Rect(C.WIDTH - 180, 20, 160, 45)
                if button_rect.collidepoint(mouse_pos):
                    van.toggle()

                elif van.open:
                    van.handle_click(mouse_pos)

                else:
                    # Throw lasso
                    world_mx, world_my = screen_to_world(
                        mouse_pos[0], mouse_pos[1], camera_x, camera_y
                    )
                    angle     = __import__("math").atan2(world_my - player.y, world_mx - player.x)
                    cos_a     = __import__("math").cos(angle)
                    sin_a     = __import__("math").sin(angle)
                    target_x  = player.x + cos_a * C.LASSO_MAX_RANGE
                    target_y  = player.y + sin_a * C.LASSO_MAX_RANGE
                    lasso.throw(player.x, player.y, target_x, target_y)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if van.open:
                    van.handle_release(mouse_pos, player.x, player.y)

        # --------------------------------------------------------
        # UPDATE
        # --------------------------------------------------------
        if not van.open:
            keys = pygame.key.get_pressed()
            player.update(keys)

        lasso.update(horses, player.x, player.y)

        # Add freshly caught horses to van
        for h in horses:
            if h.state == "caught" and h not in van.inventory:
                van.add(h)

        for h in horses:
            h.update(horse_obstacles)

        camera_x, camera_y = update_camera(player.x, player.y)

        # --------------------------------------------------------
        # DRAW
        # --------------------------------------------------------
        draw_grass(screen, camera_x, camera_y, grass_details, flowers)
        draw_race_track(screen, track_sprite, track_rect, camera_x, camera_y)
        draw_world_characters(screen, player, horses, camera_x, camera_y)

        lasso.draw(screen, player.x, player.y, camera_x, camera_y)

        # Interaction prompt
        if player.near_track(track_rect) and not van.open:
            prompt    = font.render("Press E to enter the race track", True, C.WORLD_WHITE)
            prompt_bg = pygame.Rect(C.WIDTH // 2 - 270, C.HEIGHT - 85, 540, 48)
            pygame.draw.rect(screen, C.DARK_BROWN, prompt_bg, border_radius=8)
            screen.blit(prompt, prompt.get_rect(center=prompt_bg.center))

        # Controls help bar
        ctrl_text = small_font.render(
            "WASD / Arrow keys: Drive | Left Click: Throw Lasso | E: Enter race track | ESC: Quit",
            True, C.WORLD_WHITE,
        )
        ctrl_bg = pygame.Rect(10, 10, ctrl_text.get_width() + 20, 32)
        pygame.draw.rect(screen, C.DARK_BROWN, ctrl_bg, border_radius=5)
        screen.blit(ctrl_text, (20, 17))

        # Van button
        van_btn = pygame.Rect(C.WIDTH - 180, 20, 160, 45)
        pygame.draw.rect(screen, C.DARK_TURQUOISE, van_btn, border_radius=8)
        pygame.draw.rect(screen, C.TURQUOISE, van_btn, 2, border_radius=8)
        btn_label = font.render("Close Van" if van.open else "Open Van", True, C.WORLD_WHITE)
        screen.blit(btn_label, btn_label.get_rect(center=van_btn.center))

        # Van overlay
        van.draw(screen, mouse_pos)

        pygame.display.flip()
