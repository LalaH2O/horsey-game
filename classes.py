"""
classes.py — All game-object classes for the Horsey Game.

Race-side:  Leg, RaceHorse
World-side: WorldHorse, Lasso, Van, Player
"""

import math
import random

import pygame
import pymunk

import constants as C
from constants import s


# ============================================================
# RACE-SIDE CLASSES
# ============================================================

class Leg:
    """
    One physics leg attached to a RaceHorse torso.
    Wraps a pymunk Body + SimpleMotor + joints and owns
    the waiting / moving_back / moving_forward state machine.
    """

    def __init__(
        self,
        body: pymunk.Body,
        shape: pymunk.Shape,
        joint: pymunk.PivotJoint,
        limit: pymunk.RotaryLimitJoint,
        motor: pymunk.SimpleMotor,
        hip_x: float,
        motor_force,            # float | None
        original_angle: float,
        wait_time: float,
        move_duration: float,
    ):
        self.body         = body
        self.shape        = shape
        self.joint        = joint
        self.limit        = limit
        self.motor        = motor

        self.hip_x        = hip_x
        self.motor_force  = motor_force

        self.original_angle = original_angle
        self.start_angle    = original_angle
        self.target_angle   = original_angle

        self.wait_time    = wait_time
        self.wait_timer   = 0.0
        self.move_timer   = 0.0
        self.move_duration = move_duration

        self.state = "waiting"      # "waiting" | "moving_back" | "moving_forward"

    # ------------------------------------------------------------------
    # Internal helper: drive motor toward target_angle (relative to torso)
    # ------------------------------------------------------------------
    def _move_towards(self, torso: pymunk.Body, target_angle: float) -> bool:
        """
        Spin the motor so the leg approaches *target_angle* relative to the
        torso.  Returns True when the target is reached (within tolerance).
        """
        relative_angle = self.body.angle - torso.angle
        difference     = target_angle - relative_angle

        if abs(difference) > C.ANGLE_TOLERANCE:
            self.motor.rate = (
                (1 if difference > 0 else -1)
                * C.LEG_ANGLE_SPEED
                * C.MOTOR_DIRECTION
            )
            return False

        self.motor.rate = 0
        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Hard-stop the motor (used while horse is being dragged)."""
        self.motor.rate = 0

    def update(self, dt: float, torso: pymunk.Body, leg_index: int) -> None:
        """Advance the leg FSM by *dt* seconds."""

        original = self.original_angle

        if self.state == "waiting":
            self.motor.rate = 0
            self.wait_timer += dt

            if self.wait_timer >= self.wait_time:
                self.state       = "moving_back"
                self.move_timer  = 0.0
                self.move_duration = random.uniform(C.MIN_MOVE_TIME, C.MAX_MOVE_TIME)
                self.start_angle   = self.body.angle - torso.angle

                direction = (
                    C.BACK_LEG_DIRECTION
                    if leg_index == 0
                    else C.FRONT_LEG_DIRECTION
                )
                self.target_angle = original + C.LEG_SWING_ANGLE * direction

        elif self.state == "moving_back":
            self.move_timer += dt
            t = min(1.0, self.move_timer / self.move_duration)
            interp_target = (
                self.start_angle
                + (self.target_angle - self.start_angle) * t
            )
            reached = self._move_towards(torso, interp_target)

            if reached or t >= 1.0:
                self.state       = "moving_forward"
                self.move_timer  = 0.0
                self.start_angle = self.body.angle - torso.angle
                self.target_angle = original

        elif self.state == "moving_forward":
            self.move_timer += dt
            t = min(1.0, self.move_timer / self.move_duration)
            interp_target = (
                self.start_angle
                + (self.target_angle - self.start_angle) * t
            )
            reached = self._move_towards(torso, interp_target)

            if reached or t >= 1.0:
                self.state      = "waiting"
                self.wait_timer = 0.0
                self.wait_time  = random.uniform(C.MIN_LEG_WAIT, C.MAX_LEG_WAIT)


class RaceHorse:
    """
    A horse competing on the race track.
    Owns a pymunk torso Body and a list of two Leg objects.
    """

    def __init__(
        self,
        lane: int,
        torso: pymunk.Body,
        color: tuple,
        legs: list,         # list[Leg]
        leg_lengths: list,  # list[float]
        start_angle: float,
    ):
        self.lane        = lane
        self.torso       = torso
        self.color       = color
        self.legs        = legs
        self.leg_lengths = leg_lengths
        self.start_angle = start_angle

    # ------------------------------------------------------------------
    def rect(self) -> pygame.Rect:
        """Bounding rectangle used for collision / finish-line detection."""
        x = self.torso.position.x - C.MODEL_CENTRE_X * C.SCALE
        y = self.torso.position.y - C.MODEL_CENTRE_Y * C.SCALE
        extra_height = max(self.leg_lengths) - C.DEFAULT_LEG_LENGTH * C.SCALE

        return pygame.Rect(
            int(x + C.HORSE_LEFT  * C.SCALE),
            int(y + C.HORSE_TOP   * C.SCALE),
            int((C.HORSE_RIGHT - C.HORSE_LEFT) * C.SCALE),
            int((C.HORSE_BOTTOM - C.HORSE_TOP) * C.SCALE + extra_height),
        )

    def update(self, dt: float, is_dragged: bool) -> None:
        """Step the leg FSMs; skip if the horse is currently being dragged."""
        if is_dragged:
            for leg in self.legs:
                leg.stop()
            return

        for leg_index, leg in enumerate(self.legs):
            leg.update(dt, self.torso, leg_index)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw legs, body and head onto *surface*."""
        from methods import draw_horse_body, draw_leg  # avoid circular imports at module level

        # Back leg first (drawn behind body)
        draw_leg(surface, self.legs[0].body, self.color, self.leg_lengths[0])
        draw_horse_body(surface, self)
        # Front leg on top
        draw_leg(surface, self.legs[1].body, self.color, self.leg_lengths[1])


# ============================================================
# WORLD-SIDE CLASSES
# ============================================================

class WorldHorse:
    """A horse wandering in the overworld map."""

    def __init__(self, traits: dict, sprite_right: pygame.Surface,
                 sprite_left: pygame.Surface, x: float, y: float):
        self.traits        = traits
        self.sprite_right  = sprite_right
        self.sprite_left   = sprite_left
        self.x             = x
        self.y             = y
        self.w             = sprite_right.get_width()
        self.h             = sprite_right.get_height()
        self.direction     = random.choice([1, -1])
        self.state         = "idle"      # "idle" | "walk" | "caught"
        self.timer         = random.randint(C.FPS_WORLD, C.FPS_WORLD * 3)
        self.dx            = 0.0
        self.dy            = 0.0

    # ------------------------------------------------------------------
    def rect_at(self, x: float, y: float) -> pygame.Rect:
        return pygame.Rect(
            int(x - self.w / 2),
            int(y - self.h),
            self.w,
            self.h,
        )

    def can_stand(self, x: float, y: float, obstacles: list) -> bool:
        rect = self.rect_at(x, y)
        if rect.left < 20 or rect.right > C.WORLD_WIDTH - 20:
            return False
        if rect.top < 20 or y > C.WORLD_HEIGHT - 10:
            return False
        for obstacle in obstacles:
            if rect.colliderect(obstacle):
                return False
        return True

    def stop(self) -> None:
        self.state  = "idle"
        self.timer  = random.randint(C.FPS_WORLD * 1, C.FPS_WORLD * 3)
        self.dx     = 0.0
        self.dy     = 0.0

    def start_walking(self) -> None:
        dx, dy = random.choice(C.HORSE_DIRECTIONS)
        self.state  = "walk"
        self.timer  = random.randint(C.FPS_WORLD * 1, C.FPS_WORLD * 4)
        self.dx     = dx
        self.dy     = dy
        if dx > 0:
            self.direction = 1
        elif dx < 0:
            self.direction = -1

    def update(self, obstacles: list) -> None:
        if self.state == "caught":
            return

        self.timer -= 1

        if self.state == "idle":
            if self.timer <= 0:
                self.start_walking()
            return

        new_x = self.x + self.dx * C.HORSE_SPEED_WORLD
        new_y = self.y + self.dy * C.HORSE_SPEED_WORLD

        if self.can_stand(new_x, new_y, obstacles):
            self.x = new_x
            self.y = new_y
            if self.timer <= 0:
                self.stop()
        else:
            self.stop()

    def draw(self, screen: pygame.Surface,
             camera_x: float, camera_y: float,
             screen_w: int, screen_h: int) -> None:
        if self.state == "caught":
            return

        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)

        sprite = self.sprite_right if self.direction == 1 else self.sprite_left
        rect   = sprite.get_rect(midbottom=(sx, sy))

        if rect.right < 0 or rect.left > screen_w:
            return
        if rect.bottom < 0 or rect.top > screen_h:
            return

        screen.blit(sprite, rect)


class Lasso:
    """
    Throw-and-reel lasso mechanic.
    Call throw() on click, update() every frame, draw() to render.
    """

    def __init__(self):
        self.active       = False
        self.pos          = [0.0, 0.0]
        self.target_pos   = [0.0, 0.0]
        self.progress     = 1.0        # 0 → 1 traveling out, then returns
        self.caught_horse = None       # WorldHorse | None

    def throw(self, from_x: float, from_y: float,
              target_x: float, target_y: float) -> None:
        if self.active:
            return
        self.active       = True
        self.pos          = [from_x, from_y]
        self.target_pos   = [target_x, target_y]
        self.progress     = 0.0
        self.caught_horse = None

    def update(self, horses: list, car_x: float, car_y: float) -> None:
        if not self.active:
            return

        step = C.LASSO_SPEED / C.LASSO_MAX_RANGE

        if self.caught_horse is None:
            # Traveling outward
            self.progress += step
            if self.progress >= 1.0:
                self.progress = 1.0
                # Check hit
                hit = None
                for h in horses:
                    if h.state != "caught":
                        dist = math.hypot(
                            h.x - self.target_pos[0],
                            h.y - self.target_pos[1],
                        )
                        if dist < 60:
                            hit = h
                            break
                if hit:
                    self.caught_horse       = hit
                    self.caught_horse.state = "caught"
                else:
                    self.progress = 1.05   # trigger empty return
        else:
            # Reeling in
            self.progress -= step
            self.caught_horse.x = (
                car_x + (self.target_pos[0] - car_x) * max(0.0, self.progress)
            )
            self.caught_horse.y = (
                car_y + (self.target_pos[1] - car_y) * max(0.0, self.progress)
            )
            if self.progress <= 0.0:
                self.active       = False
                self.caught_horse = None      # caller adds to van inventory
                return

        # Empty return
        if self.progress > 1.0 and self.caught_horse is None:
            self.progress -= step
            if self.progress <= 0.0:
                self.active = False

    def draw(self, screen: pygame.Surface,
             car_x: float, car_y: float,
             camera_x: float, camera_y: float) -> None:
        if not self.active:
            return

        car_sx = int(car_x - camera_x)
        car_sy = int(car_y - camera_y)

        if self.caught_horse is None:
            curr_x = car_x + (self.target_pos[0] - car_x) * min(1.0, self.progress)
            curr_y = car_y + (self.target_pos[1] - car_y) * min(1.0, self.progress)
        else:
            curr_x = self.caught_horse.x
            curr_y = self.caught_horse.y

        curr_sx = int(curr_x - camera_x)
        curr_sy = int(curr_y - camera_y)

        pygame.draw.line(screen, C.WHITE, (car_sx, car_sy), (curr_sx, curr_sy), 3)
        pygame.draw.circle(screen, C.GOLD, (curr_sx, curr_sy), 14, 2)


class Van:
    """Player's horse trailer — inventory storage and UI overlay."""

    def __init__(self):
        self.inventory      = []          # list[WorldHorse]
        self.open           = False
        self.dragging_horse = None        # WorldHorse | None
        self.drag_offset_x  = 0
        self.drag_offset_y  = 0
        self.drag_start_pos = (0, 0)

    # ------------------------------------------------------------------
    def toggle(self) -> None:
        self.open           = not self.open
        self.dragging_horse = None

    def handle_click(self, mouse_pos: tuple) -> None:
        """Check if a horse slot was clicked; start dragging if so."""
        container_rect = pygame.Rect(
            C.WIDTH // 2 - 350, C.HEIGHT // 2 - 250, 700, 500
        )
        if not container_rect.collidepoint(mouse_pos):
            return

        slot_x = container_rect.x + 30
        slot_y = container_rect.y + 80

        for idx, h in enumerate(self.inventory):
            item_rect = pygame.Rect(
                slot_x + (idx % 4) * 160,
                slot_y + (idx // 4) * 160,
                140, 140,
            )
            if item_rect.collidepoint(mouse_pos):
                self.dragging_horse  = h
                self.drag_offset_x   = mouse_pos[0] - item_rect.x
                self.drag_offset_y   = mouse_pos[1] - item_rect.y
                self.drag_start_pos  = mouse_pos
                break

    def handle_release(self, mouse_pos: tuple,
                       car_x: float, car_y: float) -> None:
        """Drop a dragged horse; release to world if outside the container."""
        if self.dragging_horse is None:
            return

        container_rect = pygame.Rect(
            C.WIDTH // 2 - 350, C.HEIGHT // 2 - 250, 700, 500
        )
        if not container_rect.collidepoint(mouse_pos):
            # Release back into the world near the car
            self.dragging_horse.x     = car_x + random.randint(-60, 60)
            self.dragging_horse.y     = car_y + random.randint(40, 80)
            self.dragging_horse.state = "idle"
            self.inventory.remove(self.dragging_horse)

        self.dragging_horse = None

    def add(self, horse) -> None:
        if horse not in self.inventory:
            self.inventory.append(horse)

    def draw(self, screen: pygame.Surface, mouse_pos: tuple) -> None:
        """Draw the full inventory overlay."""
        if not self.open:
            return

        overlay = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        container_rect = pygame.Rect(
            C.WIDTH // 2 - 350, C.HEIGHT // 2 - 250, 700, 500
        )
        pygame.draw.rect(screen, C.DARK_BROWN, container_rect, border_radius=12)
        pygame.draw.rect(screen, C.WOOD, container_rect, 4, border_radius=12)

        from methods import get_font
        title_font = get_font(30, bold=True)
        small_font = get_font(17)

        title_surf = title_font.render(
            f"Van Inventory (Horses Caught: {len(self.inventory)})",
            True, C.GOLD,
        )
        screen.blit(
            title_surf,
            title_surf.get_rect(center=(container_rect.centerx, container_rect.y + 35)),
        )

        inst_surf = small_font.render(
            "Drag horses outside this container to release them back into the world!",
            True, C.WORLD_WHITE,
        )
        screen.blit(
            inst_surf,
            inst_surf.get_rect(center=(container_rect.centerx, container_rect.bottom - 25)),
        )

        slot_x = container_rect.x + 30
        slot_y = container_rect.y + 80

        for idx, h in enumerate(self.inventory):
            if h is self.dragging_horse:
                continue

            item_rect = pygame.Rect(
                slot_x + (idx % 4) * 160,
                slot_y + (idx // 4) * 160,
                140, 140,
            )
            pygame.draw.rect(screen, (50, 40, 30), item_rect, border_radius=8)
            pygame.draw.rect(screen, C.GOLD, item_rect, 2, border_radius=8)

            mini = pygame.transform.smoothscale(h.sprite_right, (100, 50))
            screen.blit(mini, mini.get_rect(center=item_rect.center))

        # Dragged horse follows cursor
        if self.dragging_horse is not None:
            dx = mouse_pos[0] - self.drag_offset_x
            dy = mouse_pos[1] - self.drag_offset_y
            drag_rect = pygame.Rect(dx, dy, 140, 140)
            pygame.draw.rect(screen, (70, 60, 40), drag_rect, border_radius=8)
            pygame.draw.rect(screen, C.WORLD_WHITE, drag_rect, 2, border_radius=8)
            mini = pygame.transform.smoothscale(self.dragging_horse.sprite_right, (100, 50))
            screen.blit(mini, mini.get_rect(center=drag_rect.center))


class Player:
    """The player-controlled van/car."""

    def __init__(self, x: float, y: float):
        self.x         = x
        self.y         = y
        self.direction = 1    # 1 = right, -1 = left

        from methods import build_vehicle_sprite
        self._sprite_right = build_vehicle_sprite(flip=False)
        self._sprite_left  = build_vehicle_sprite(flip=True)

    # ------------------------------------------------------------------
    def update(self, keys) -> None:
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x        += C.MOVE_SPEED
            self.direction = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x        -= C.MOVE_SPEED
            self.direction = -1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= C.MOVE_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += C.MOVE_SPEED

        self.x = max(45, min(C.WORLD_WIDTH  - 45, self.x))
        self.y = max(45, min(C.WORLD_HEIGHT - 45, self.y))

    def near_track(self, track_rect: pygame.Rect) -> bool:
        player_rect      = pygame.Rect(int(self.x - 35), int(self.y - 35), 70, 70)
        interaction_area = track_rect.inflate(100, 100)
        return player_rect.colliderect(interaction_area)

    def draw(self, screen: pygame.Surface,
             camera_x: float, camera_y: float) -> None:
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        sprite = self._sprite_right if self.direction == 1 else self._sprite_left
        screen.blit(sprite, sprite.get_rect(center=(sx, sy)))

    @property
    def feet_y(self) -> float:
        """Y-coordinate of the bottom of the vehicle sprite (for depth sorting)."""
        return self.y + C.SPRITE_ROWS * C.CELL / 2
