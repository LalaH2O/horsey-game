import math

# ============================================================
# SCREEN SETTINGS
# ============================================================

WIDTH, HEIGHT = 2560, 1440
FPS_TRACK = 60
FPS_WORLD = 240

BASE_WIDTH, BASE_HEIGHT = 1000, 700
U = min(WIDTH / BASE_WIDTH, HEIGHT / BASE_HEIGHT)

WORLD_SIZE = (1000, 700)
WORLD_WIDTH = 3200
WORLD_HEIGHT = 2000


def s(value):
    """Scale a pixel value designed for 1000 x 700 to this screen."""
    return int(value * U)


# ============================================================
# COLOURS  (track palette wins on conflicts)
# ============================================================

SKY_BLUE    = (135, 206, 235)
GRASS_BG    = (152, 251, 152)
LINE        = (238, 203, 117)

DARK        = (72, 47, 16)
WHITE       = (255, 255, 255)
BLACK       = (20, 18, 8)
GOLD        = (255, 215, 0)
LOSE_RED    = (255, 120, 120)

HORSE_COLORS = [
    (215, 148, 45),
    (145, 75, 48),
    (175, 175, 175),
    (100, 135, 75),
]

# World colours
GRASS        = (100, 165, 75)
DARK_GRASS   = (80, 140, 60)
LIGHT_GRASS  = (120, 180, 85)

BROWN        = (116, 75, 43)
DARK_BROWN   = (76, 47, 29)
WOOD         = (158, 105, 57)

WORLD_WHITE  = (245, 245, 225)   # world version differs slightly from track WHITE
WORLD_BLACK  = (25, 25, 20)      # world version differs slightly from track BLACK

RED          = (235, 35, 70)
DARK_RED     = (165, 20, 50)

WINDOW_COLOR = (125, 190, 215)
ROOF         = (100, 45, 35)

YELLOW       = (245, 225, 35)

TURQUOISE      = (10, 195, 185)
DARK_TURQUOISE = (5, 135, 130)

TITLE_PURPLE     = (105, 75, 200)
TITLE_BG         = (240, 240, 250)
STAND_GRAY       = (195, 195, 200)
STAND_LIGHT      = (222, 222, 228)
STAND_DARK       = (140, 140, 148)
TRACK_GREEN      = (95, 190, 85)
TRACK_DARK_GREEN = (45, 125, 55)
TRACK_ORANGE     = (240, 150, 60)
TRACK_LIGHT_ORANGE = (250, 190, 110)
FLAG_PINK        = (240, 120, 170)
FLAG_GREEN       = (80, 200, 90)
FLAG_PURPLE      = (110, 70, 200)
FENCE_INNER      = (240, 235, 200)

V_TURQUOISE  = (20, 232, 224)
V_RED        = (238, 55, 90)
V_YELLOW     = (212, 225, 20)
V_WINDOW     = (245, 248, 255)
V_BLACK      = (25, 25, 30)
V_GRAY       = (150, 150, 160)
V_GRAY_LIGHT = (185, 185, 195)


# ============================================================
# TRACK LAYOUT
# ============================================================

LANE_COUNT  = 4
LANE_HEIGHT = s(165)
LANE_PAD    = s(5)

TRACK_LEFT  = s(25)
TRACK_RIGHT = WIDTH - s(25)

TRACK_TOP = max(
    s(30),
    (HEIGHT - LANE_COUNT * LANE_HEIGHT) // 2
)

START_LINE_X       = s(75)
HORSE_START_OFFSET = 45 * U

FINISH_X     = TRACK_RIGHT - s(65)
FINISH_WIDTH = s(12)

MAX_RACE_TIME = 90000


# ============================================================
# HORSE MODEL AND PHYSICS
# ============================================================

SCALE = 0.4 * U

HORSE_TOP    = -30
HORSE_BOTTOM = 478
HORSE_LEFT   = 71
HORSE_RIGHT  = 514

MODEL_CENTRE_X = 256
MODEL_CENTRE_Y = 288.5

GRAVITY      = 1200 * U
PHYSICS_STEP = 1 / 120

TORSO_MASS = 8.0
LEG_MASS   = 0.65

MIN_LEG_LENGTH     = 50
MAX_LEG_LENGTH     = 130
DEFAULT_LEG_LENGTH = 123

LEG_DIFFERENCE_CHANCE = 0.20
MIN_LEG_DIFFERENCE    = -30
MAX_LEG_DIFFERENCE    = 30

LEG_OFFSET_CHANCE = 0.80
MIN_LEG_OFFSET    = 1 * SCALE
MAX_LEG_OFFSET    = 25 * SCALE

LEG_WIDTH = 8 * SCALE

HIP_MIN_ANGLE = -0.3
HIP_MAX_ANGLE = 0.8

MIN_START_ANGLE = -0.05
MAX_START_ANGLE = 0.1

MIN_FRONT_LEG_FORCE = 20000 * U * U
MAX_FRONT_LEG_FORCE = 40000 * U * U

LEG_SWING_ANGLE  = 1.2
LEG_ANGLE_SPEED  = 4
ANGLE_TOLERANCE  = 0.025

MOTOR_DIRECTION     = -1
BACK_LEG_DIRECTION  = 1
FRONT_LEG_DIRECTION = -1

MIN_LEG_WAIT  = 0
MAX_LEG_WAIT  = 0.1
MIN_MOVE_TIME = 0.1
MAX_MOVE_TIME = 0.4


# ============================================================
# BETTING
# ============================================================

STARTING_MONEY = 1000
PAYOUT_ODDS    = 2
MIN_BET        = 10
BET_STEP       = 10


# ============================================================
# WORLD / PLAYER
# ============================================================

MOVE_SPEED  = 2.0
HORSE_COUNT = 8

LASSO_MAX_RANGE = 450.0
LASSO_SPEED     = 15.0

# World horse rendering
WORLD_HORSE_SCALE  = 0.22
HORSE_SPEED_WORLD  = MOVE_SPEED * 0.3
TILT_UNEVEN_LEGS   = True
HORSE_SUPERSAMPLE  = 4
HORSE_HOOF         = [(-15, -7.5), (15, -7.5), (22.5, 7.5), (-15, 7.5)]

HORSE_DIRECTIONS = [
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (0.7071, 0.7071), (-0.7071, 0.7071),
    (0.7071, -0.7071), (-0.7071, -0.7071),
]

# Vehicle sprite dimensions
CELL        = 5
SPRITE_COLS = 38
SPRITE_ROWS = 16

# World race-track sprite dimensions
TRACK_CELL = 9
TRACK_COLS = 66
TRACK_ROWS = 50
