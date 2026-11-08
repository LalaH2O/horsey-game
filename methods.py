"""
methods.py — Pure helper functions for the Horsey Game.

Drawing helpers, physics helpers, sprite builders, camera math.
Imported by both track.py and world.py.
"""

import math
import random

import pygame
import pymunk

import constants as C
from constants import s


# ============================================================
# FONT CACHE
# ============================================================

_font_cache: dict = {}


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("Arial", size, bold=bold)
    return _font_cache[key]


# ============================================================
# MODEL / DRAWING HELPERS  (track)
# ============================================================

def model_point(x: float, y: float, angle: float,
                px: float, py: float) -> tuple:
    """Transform a model-space point into world-space for drawing."""
    local_x = (px - C.MODEL_CENTRE_X) * C.SCALE
    local_y = (py - C.MODEL_CENTRE_Y) * C.SCALE

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    world_x = x + local_x * cos_a - local_y * sin_a
    world_y = y + local_x * sin_a + local_y * cos_a

    return int(world_x), int(world_y)


def draw_horse_body(surface: pygame.Surface, horse) -> None:
    """Draw the torso, neck, head and details of a RaceHorse."""
    torso = horse.torso
    x     = torso.position.x
    y     = torso.position.y
    angle = torso.angle
    color = horse.color

    def point(px, py):
        return model_point(x, y, angle, px, py)

    def poly(c, points):
        pygame.draw.polygon(
            surface, c,
            [point(px, py) for px, py in points],
        )

    # Tail
    poly(color, [(127,222),(71,301),(87,310),(127,222)])
    # Body
    poly(color, [(126,222),(386,222),(386,355),(126,355)])
    # Neck
    poly(color, [(367,222),(417,171),(426,143),(424,110),(462,151),(435,193),(386,242)])
    # Head
    poly(color, [(424,110),(462,151),(502,166),(495,210),(436,193),(417,171)])
    # Ear
    poly(color, [(424,110),(424,143),(435,153),(438,150)])
    # Muzzle
    poly(color, [(495,166),(513,173),(508,185),(495,181)])
    # Eye
    pygame.draw.circle(surface, C.WHITE, point(453,159), max(1, int(4 * C.SCALE)))
    pygame.draw.circle(surface, C.BLACK, point(454,159), max(1, int(2 * C.SCALE)))
    # Nose
    poly(C.BLACK, [(501,171),(514,175),(511,185),(499,181)])
    # Mouth
    poly(C.WHITE, [(472,190),(494,196),(492,201),(471,195)])


def draw_leg(surface: pygame.Surface,
             leg: pymunk.Body,
             color: tuple,
             leg_length: float) -> None:
    """Draw one physics leg as a thick segment with a hoof."""
    top    = leg.local_to_world((0, -leg_length / 2))
    bottom = leg.local_to_world((0,  leg_length / 2))

    dx = bottom.x - top.x
    dy = bottom.y - top.y
    length = max(1, math.hypot(dx, dy))

    nx = -dy / length
    ny =  dx / length

    hw = C.LEG_WIDTH * 0.65
    pts = [
        (top.x    + nx * hw, top.y    + ny * hw),
        (top.x    - nx * hw, top.y    - ny * hw),
        (bottom.x - nx * hw, bottom.y - ny * hw),
        (bottom.x + nx * hw, bottom.y + ny * hw),
    ]
    pygame.draw.polygon(surface, color, [(int(px), int(py)) for px, py in pts])

    # Hoof
    hoof_center = leg.local_to_world((0, leg_length / 2 - 2 * C.U))
    hoof_local  = [(-6*C.U, -3*C.U), (6*C.U, -3*C.U), (9*C.U, 3*C.U), (-6*C.U, 3*C.U)]
    cos_a = math.cos(leg.angle)
    sin_a = math.sin(leg.angle)

    hoof_pts = []
    for px, py in hoof_local:
        hoof_pts.append((
            int(hoof_center.x + px * cos_a - py * sin_a),
            int(hoof_center.y + px * sin_a + py * cos_a),
        ))
    pygame.draw.polygon(surface, C.DARK, hoof_pts)


def draw_horses(surface: pygame.Surface, horses: list) -> None:
    """Draw all RaceHorse objects in *horses*."""
    for horse in horses:
        horse.draw(surface)


# ============================================================
# TRACK DRAWING  (track)
# ============================================================

def draw_track(screen: pygame.Surface, bet_info=None) -> None:
    """Draw the race-track background, lanes, start/finish lines."""
    screen.fill(C.GRASS_BG)

    sky_height = C.TRACK_TOP
    if sky_height > 0:
        pygame.draw.rect(screen, C.SKY_BLUE, (0, 0, C.WIDTH, sky_height))

    font       = get_font(s(32), bold=True)
    line_width = max(1, s(2))
    inner_h    = C.LANE_HEIGHT - C.LANE_PAD

    for i in range(C.LANE_COUNT):
        y = C.TRACK_TOP + i * C.LANE_HEIGHT

        pygame.draw.line(screen, C.LINE, (0, y), (C.WIDTH, y), line_width)
        pygame.draw.line(screen, C.LINE, (0, y + inner_h), (C.WIDTH, y + inner_h), line_width)

        label = font.render(str(i + 1), True, C.WHITE)
        screen.blit(label, (s(12), y + s(55)))

    # Starting line
    pygame.draw.line(
        screen, C.WHITE,
        (C.START_LINE_X, C.TRACK_TOP),
        (C.START_LINE_X, C.TRACK_TOP + (C.LANE_COUNT - 1) * C.LANE_HEIGHT + inner_h),
        max(1, s(3)),
    )

    # Finish line
    pygame.draw.rect(
        screen, C.WHITE,
        (C.FINISH_X, C.TRACK_TOP,
         C.FINISH_WIDTH, (C.LANE_COUNT - 1) * C.LANE_HEIGHT + inner_h),
    )

    # Bet info
    if bet_info is not None:
        bet_font = get_font(s(22), bold=True)
        bet_text = bet_font.render(
            f"Your Bet: Horse {bet_info[0] + 1} (${bet_info[1]})",
            True, C.GOLD,
        )
        screen.blit(bet_text, (s(50), s(10)))


def lane_rect(lane: int) -> pygame.Rect:
    """Return the clickable rectangle for a betting lane."""
    return pygame.Rect(
        C.TRACK_LEFT,
        C.TRACK_TOP + lane * C.LANE_HEIGHT,
        C.TRACK_RIGHT - C.TRACK_LEFT,
        C.LANE_HEIGHT - C.LANE_PAD,
    )


# ============================================================
# CAMERA HELPERS  (world)
# ============================================================

def world_to_screen(x: float, y: float,
                    camera_x: float, camera_y: float) -> tuple:
    return int(x - camera_x), int(y - camera_y)


def screen_to_world(sx: float, sy: float,
                    camera_x: float, camera_y: float) -> tuple:
    return sx + camera_x, sy + camera_y


def update_camera(car_x: float, car_y: float) -> tuple:
    """Return (camera_x, camera_y) centred on the player."""
    cx = max(0, min(C.WORLD_WIDTH  - C.WIDTH,  car_x - C.WIDTH  // 2))
    cy = max(0, min(C.WORLD_HEIGHT - C.HEIGHT, car_y - C.HEIGHT // 2))
    return cx, cy


# ============================================================
# WORLD GRASS / ENVIRONMENT DRAWING
# ============================================================

def draw_grass(screen: pygame.Surface,
               camera_x: float, camera_y: float,
               grass_details: list,
               flowers: list) -> None:
    screen.fill(C.GRASS)

    for x, y, color in grass_details:
        sx, sy = int(x - camera_x), int(y - camera_y)
        if -15 <= sx <= C.WIDTH + 15 and -15 <= sy <= C.HEIGHT + 15:
            pygame.draw.rect(screen, color, (sx, sy, 9, 9))

    patches = [
        (200,200),(450,350),(900,700),(1200,400),
        (1500,800),(700,850),(300,750),(1600,250),
    ]
    for x, y in patches:
        sx, sy = int(x - camera_x), int(y - camera_y)
        pygame.draw.rect(screen, C.DARK_GRASS,  (sx,      sy,      24, 12))
        pygame.draw.rect(screen, C.LIGHT_GRASS, (sx + 8,  sy + 12, 16,  8))

    for x, y, color in flowers:
        sx, sy = int(x - camera_x), int(y - camera_y)
        if -5 <= sx <= C.WIDTH + 5 and -5 <= sy <= C.HEIGHT + 5:
            pygame.draw.rect(screen, color, (sx, sy, 6, 6))


# ============================================================
# WORLD RACE-TRACK SPRITE BUILDER
# ============================================================

def build_race_track_sprite() -> pygame.Surface:
    grid = [[None] * C.TRACK_COLS for _ in range(C.TRACK_ROWS)]

    def fill(c0, r0, c1, r1, color):
        for r in range(max(0, r0), min(C.TRACK_ROWS, r1 + 1)):
            for c in range(max(0, c0), min(C.TRACK_COLS, c1 + 1)):
                grid[r][c] = color

    def outline(c0, r0, c1, r1, color):
        for c in range(c0, c1 + 1):
            grid[r0][c] = color
            grid[r1][c] = color
        for r in range(r0, r1 + 1):
            grid[r][c0] = color
            grid[r][c1] = color

    # Title banner
    fill(13,2,52,9, C.TITLE_BG);     outline(13,2,52,9, C.DARK_BROWN)
    # R
    fill(15,4,15,7, C.TITLE_PURPLE); fill(16,4,17,4, C.TITLE_PURPLE)
    fill(17,5,17,5, C.TITLE_PURPLE); fill(16,6,16,6, C.TITLE_PURPLE)
    fill(17,7,17,7, C.TITLE_PURPLE)
    # A
    fill(19,5,19,7, C.TITLE_PURPLE); fill(20,4,20,4, C.TITLE_PURPLE)
    fill(21,5,21,7, C.TITLE_PURPLE); fill(20,6,20,6, C.TITLE_PURPLE)
    # C
    fill(23,4,25,4, C.TITLE_PURPLE); fill(23,5,23,7, C.TITLE_PURPLE)
    fill(24,7,25,7, C.TITLE_PURPLE)
    # E
    fill(27,4,29,4, C.TITLE_PURPLE); fill(27,5,27,7, C.TITLE_PURPLE)
    fill(28,5,28,6, C.TITLE_PURPLE); fill(27,7,29,7, C.TITLE_PURPLE)
    # T
    fill(32,4,34,4, C.TITLE_PURPLE); fill(33,5,33,7, C.TITLE_PURPLE)
    # R
    fill(36,4,36,7, C.TITLE_PURPLE); fill(37,4,38,4, C.TITLE_PURPLE)
    fill(38,5,38,5, C.TITLE_PURPLE); fill(37,6,37,6, C.TITLE_PURPLE)
    fill(38,7,38,7, C.TITLE_PURPLE)
    # A
    fill(40,5,40,7, C.TITLE_PURPLE); fill(41,4,41,4, C.TITLE_PURPLE)
    fill(42,5,42,7, C.TITLE_PURPLE); fill(41,6,41,6, C.TITLE_PURPLE)
    # C
    fill(44,4,46,4, C.TITLE_PURPLE); fill(44,5,44,7, C.TITLE_PURPLE)
    fill(45,7,46,7, C.TITLE_PURPLE)
    # K
    fill(48,4,48,7, C.TITLE_PURPLE)
    grid[5][49] = C.TITLE_PURPLE; grid[6][50] = C.TITLE_PURPLE
    fill(51,4,51,4, C.TITLE_PURPLE); fill(51,7,51,7, C.TITLE_PURPLE)

    # Grandstands
    flag_colors = (C.FLAG_PINK, C.FLAG_GREEN, C.FLAG_PURPLE)
    for i in range(3):
        gx = 18 + i * 10
        fill(gx,12,gx+8,13, C.STAND_LIGHT); outline(gx,12,gx+8,13, C.STAND_DARK)
        fill(gx,14,gx+8,23, C.STAND_GRAY);  outline(gx,14,gx+8,23, C.STAND_DARK)
        for ry in (16, 19, 21):
            for cx in range(gx + 1, gx + 8):
                grid[ry][cx] = C.STAND_DARK
        pole_x = gx + 4
        for py in range(7, 12):
            grid[py][pole_x] = C.STAND_DARK
        fill(pole_x+1,7,pole_x+4,10, flag_colors[i])

    # Oval track
    fill(8,25,57,45,  C.TRACK_GREEN);        outline(8,25,57,45,  C.TRACK_DARK_GREEN)
    fill(13,29,52,41, C.TRACK_ORANGE);       outline(13,29,52,41, C.TRACK_LIGHT_ORANGE)
    fill(32,29,34,36, C.WHITE)

    # Fence
    fill(3,30,9,40,   C.BROWN);              outline(3,30,9,40,   C.DARK_BROWN)
    fill(4,33,8,37,   C.FENCE_INNER)
    for fx in range(4, 9, 2):
        grid[31][fx] = C.DARK_BROWN
        grid[39][fx] = C.DARK_BROWN

    # Gate
    fill(0,27,2,43,   C.STAND_GRAY);         outline(0,27,2,43,   C.STAND_DARK)
    fill(1,30,1,40,   C.WHITE)

    surface = pygame.Surface(
        (C.TRACK_COLS * C.TRACK_CELL, C.TRACK_ROWS * C.TRACK_CELL),
        pygame.SRCALPHA,
    )
    for r in range(C.TRACK_ROWS):
        for c in range(C.TRACK_COLS):
            color = grid[r][c]
            if color is not None:
                pygame.draw.rect(
                    surface, color,
                    (c * C.TRACK_CELL, r * C.TRACK_CELL, C.TRACK_CELL, C.TRACK_CELL),
                )
    return surface


def draw_race_track(screen: pygame.Surface,
                    track_sprite: pygame.Surface,
                    track_rect: pygame.Rect,
                    camera_x: float, camera_y: float) -> None:
    sx, sy = int(track_rect.x - camera_x), int(track_rect.y - camera_y)
    screen.blit(track_sprite, (sx, sy))


# ============================================================
# VEHICLE SPRITE BUILDER  (world)
# ============================================================

def build_vehicle_sprite(flip: bool = False) -> pygame.Surface:
    grid = [[None] * C.SPRITE_COLS for _ in range(C.SPRITE_ROWS)]

    def fill(c0, r0, c1, r1, color):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = color

    # Trailer
    fill(0,0,21,0,  C.V_TURQUOISE); fill(0,1,22,1, C.V_TURQUOISE)
    fill(0,2,23,2,  C.V_TURQUOISE); fill(0,3,24,3, C.V_TURQUOISE)
    fill(0,4,25,12, C.V_TURQUOISE)
    for wc in (3, 10, 16):
        fill(wc,3,wc+2,3, C.V_WINDOW)

    # Truck body
    fill(19,8,35,8, C.V_RED); fill(19,9,36,9,  C.V_RED)
    fill(19,10,37,11,C.V_RED);fill(19,12,36,12,C.V_RED)

    # Cab
    fill(28,4,30,4, C.V_RED);    fill(27,5,27,5, C.V_RED)
    fill(28,5,30,5, C.V_WINDOW); fill(31,5,31,5, C.V_RED)
    fill(27,6,27,6, C.V_RED);    fill(28,6,30,6, C.V_WINDOW)
    fill(31,6,32,6, C.V_RED);    fill(27,7,27,7, C.V_RED)
    fill(28,7,30,7, C.V_WINDOW); fill(31,7,33,7, C.V_RED)

    # Stripes
    fill(21,9,27,9,  C.V_YELLOW); fill(23,10,26,10,C.V_YELLOW)
    fill(31,9,34,9,  C.V_YELLOW); fill(30,10,33,10,C.V_YELLOW)

    # Wheels
    def wheel(c0):
        fill(c0+1,12,c0+2,12,C.V_BLACK)
        fill(c0,13,c0+3,14, C.V_BLACK)
        fill(c0+1,15,c0+2,15,C.V_BLACK)
        grid[13][c0+1] = C.V_GRAY
        grid[13][c0+2] = C.V_GRAY_LIGHT
        grid[14][c0+1] = C.V_GRAY_LIGHT
        grid[14][c0+2] = C.V_GRAY

    for wc in (1, 7, 22, 32):
        wheel(wc)

    surface = pygame.Surface(
        (C.SPRITE_COLS * C.CELL, C.SPRITE_ROWS * C.CELL), pygame.SRCALPHA
    )
    for r in range(C.SPRITE_ROWS):
        for c in range(C.SPRITE_COLS):
            color = grid[r][c]
            if color is not None:
                pygame.draw.rect(
                    surface, color,
                    (c * C.CELL, r * C.CELL, C.CELL, C.CELL),
                )

    if flip:
        surface = pygame.transform.flip(surface, True, False)
    return surface


# ============================================================
# WORLD HORSE SPRITE BUILDER
# ============================================================

def roll_world_horse_traits() -> dict:
    if random.random() < C.LEG_DIFFERENCE_CHANCE:
        leg_difference = random.uniform(C.MIN_LEG_DIFFERENCE, C.MAX_LEG_DIFFERENCE)
    else:
        leg_difference = 0

    max_possible   = C.MAX_LEG_LENGTH - C.MIN_LEG_LENGTH
    leg_difference = max(-max_possible, min(max_possible, leg_difference))

    back_low  = max(C.MIN_LEG_LENGTH, C.MIN_LEG_LENGTH - leg_difference)
    back_high = min(C.MAX_LEG_LENGTH, C.MAX_LEG_LENGTH - leg_difference)
    back_length  = random.uniform(back_low, back_high)
    front_length = back_length + leg_difference

    if random.random() < C.LEG_OFFSET_CHANCE:
        magnitude  = random.uniform(C.MIN_LEG_OFFSET, C.MAX_LEG_OFFSET)
        shift_ratio = magnitude / C.MAX_LEG_OFFSET
        leg_shift  = magnitude * shift_ratio / C.SCALE
    else:
        leg_shift = 0

    start_angle = random.uniform(C.MIN_START_ANGLE, C.MAX_START_ANGLE)

    return {
        "color":        random.choice(C.HORSE_COLORS),
        "back_length":  back_length,
        "front_length": front_length,
        "back_hip_x":   C.MODEL_CENTRE_X - 120 + leg_shift,
        "front_hip_x":  C.MODEL_CENTRE_X + 120 - leg_shift,
        "start_angle":  start_angle,
    }


def build_horse_sprite(traits: dict) -> pygame.Surface:
    color        = traits["color"]
    back_length  = traits["back_length"]
    front_length = traits["front_length"]
    back_hip_x   = traits["back_hip_x"]
    front_hip_x  = traits["front_hip_x"]
    start_angle  = traits["start_angle"]

    ss = C.HORSE_SUPERSAMPLE
    k  = C.WORLD_HORSE_SCALE * ss

    hip_y = C.MODEL_CENTRE_Y + 66.5
    theta = 0.0

    if C.TILT_UNEVEN_LEGS:
        theta = math.atan2(back_length - front_length, front_hip_x - back_hip_x)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    pivot_x = C.MODEL_CENTRE_X
    pivot_y = hip_y

    canvas_size = int(800 * k)
    origin      = 100 * k

    big = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
    big.fill((color[0], color[1], color[2], 0))

    def pt(px, py):
        dx = px - pivot_x; dy = py - pivot_y
        rx = pivot_x + dx * cos_t - dy * sin_t
        ry = pivot_y + dx * sin_t + dy * cos_t
        return int(round(origin + rx * k)), int(round(origin + ry * k))

    def poly(c, points):
        pygame.draw.polygon(big, c, [pt(px, py) for px, py in points])

    def draw_world_leg(hip_x, length, angle):
        dir_x = -math.sin(angle)
        dir_y =  math.cos(angle)
        top_x    = hip_x;             top_y    = hip_y
        bottom_x = top_x + dir_x * length; bottom_y = top_y + dir_y * length

        nx = -dir_y; ny = dir_x
        hw = 8 * 0.65
        poly(color, [
            (top_x + nx*hw, top_y + ny*hw),
            (top_x - nx*hw, top_y - ny*hw),
            (bottom_x - nx*hw, bottom_y - ny*hw),
            (bottom_x + nx*hw, bottom_y + ny*hw),
        ])
        hoof_x = top_x + dir_x * (length - 5)
        hoof_y = top_y + dir_y * (length - 5)
        cos_a = math.cos(angle); sin_a = math.sin(angle)
        hoof_pts = [
            (hoof_x + px*cos_a - py*sin_a, hoof_y + px*sin_a + py*cos_a)
            for px, py in C.HORSE_HOOF
        ]
        poly(C.DARK, hoof_pts)

    draw_world_leg(back_hip_x, back_length, -start_angle)

    poly(color, [(127,222),(71,301),(87,310),(127,222)])
    poly(color, [(126,222),(386,222),(386,355),(126,355)])
    poly(color, [(367,222),(417,171),(426,143),(424,110),(462,151),(435,193),(386,242)])
    poly(color, [(424,110),(462,151),(502,166),(495,210),(436,193),(417,171)])
    poly(color, [(424,110),(424,143),(435,153),(438,150)])
    poly(color, [(495,166),(513,173),(508,185),(495,181)])
    pygame.draw.circle(big, C.WHITE, pt(453,159), max(1, int(round(4 * k))))
    pygame.draw.circle(big, C.BLACK, pt(454,159), max(1, int(round(2 * k))))
    poly(C.BLACK, [(501,171),(514,175),(511,185),(499,181)])
    poly(C.WHITE, [(472,190),(494,196),(492,201),(471,195)])

    draw_world_leg(front_hip_x, front_length, start_angle)

    bounds  = big.get_bounding_rect()
    cropped = big.subsurface(bounds).copy()
    width   = max(1, int(round(bounds.width  / ss)))
    height  = max(1, int(round(bounds.height / ss)))
    return pygame.transform.smoothscale(cropped, (width, height))


# ============================================================
# DEPTH-SORTED WORLD DRAWING
# ============================================================

def draw_world_characters(screen: pygame.Surface,
                           player,          # Player instance
                           horses: list,    # list[WorldHorse]
                           camera_x: float,
                           camera_y: float) -> None:
    """Draw world horses and the player vehicle in y-sorted order."""
    items = [
        (h.y, h)
        for h in horses
        if h.state != "caught"
    ]
    items.append((player.feet_y, None))
    items.sort(key=lambda item: item[0])

    for _, obj in items:
        if obj is None:
            player.draw(screen, camera_x, camera_y)
        else:
            obj.draw(screen, camera_x, camera_y, C.WIDTH, C.HEIGHT)
