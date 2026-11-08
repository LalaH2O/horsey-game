"""
track.py — Race track game loop.

Responsible for:
  - Building the physics world (create_race)
  - Running the betting screen (betting_screen)
  - Running the main race loop (run_track)

All constants, drawing helpers and classes are imported from their
dedicated modules.
"""

import random

import pygame
import pymunk

import constants as C
from constants import s
from classes import Leg, RaceHorse
from methods import (
    get_font,
    draw_track,
    draw_horses,
    lane_rect,
)


# ============================================================
# MUTABLE GAME STATE
# ============================================================

player_money = C.STARTING_MONEY


# ============================================================
# PHYSICS WORLD FACTORY
# ============================================================

def create_race() -> tuple:
    """Return (space, horses) — a fresh pymunk Space and four RaceHorse objects."""

    space = pymunk.Space()
    space.gravity         = (0, C.GRAVITY)
    space.damping         = 0.995
    space.iterations      = 30
    space.collision_slop  = 0.1 * C.U

    # Ground segment for each lane
    for lane in range(C.LANE_COUNT):
        lane_top    = C.TRACK_TOP + lane * C.LANE_HEIGHT
        lane_bottom = lane_top + C.LANE_HEIGHT - C.LANE_PAD

        ground = pymunk.Segment(
            space.static_body,
            (C.TRACK_LEFT,  lane_bottom),
            (C.TRACK_RIGHT, lane_bottom),
            2 * C.U,
        )
        ground.friction   = 2.5
        ground.elasticity = 0
        space.add(ground)

    horses = []

    BASE_HIP_POSITIONS = [-120 * C.SCALE, 120 * C.SCALE]

    for i in range(C.LANE_COUNT):
        lane_top    = C.TRACK_TOP + i * C.LANE_HEIGHT
        lane_bottom = lane_top + C.LANE_HEIGHT - C.LANE_PAD

        # Random leg lengths
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
        leg_lengths  = [back_length * C.SCALE, front_length * C.SCALE]

        # Hip offsets
        if random.random() < C.LEG_OFFSET_CHANCE:
            magnitude  = random.uniform(C.MIN_LEG_OFFSET, C.MAX_LEG_OFFSET)
            shift_ratio = magnitude / C.MAX_LEG_OFFSET
            back_hip_x  = BASE_HIP_POSITIONS[0] + (magnitude * shift_ratio)
            front_hip_x = BASE_HIP_POSITIONS[1] - (magnitude * shift_ratio)
        else:
            back_hip_x  = BASE_HIP_POSITIONS[0]
            front_hip_x = BASE_HIP_POSITIONS[1]

        HIP_POSITIONS = [back_hip_x, front_hip_x]

        # Torso
        torso_x = C.HORSE_START_OFFSET + C.MODEL_CENTRE_X * C.SCALE
        torso_y = lane_bottom - 66.5 * C.SCALE - max(leg_lengths)

        torso_moment = pymunk.moment_for_box(C.TORSO_MASS, (260 * C.SCALE, 133 * C.SCALE))
        torso        = pymunk.Body(C.TORSO_MASS, torso_moment)
        torso.position = (torso_x, torso_y)

        torso_shape           = pymunk.Poly.create_box(torso, (260 * C.SCALE, 133 * C.SCALE))
        torso_shape.friction  = 0.8
        torso_shape.elasticity = 0
        torso_shape.filter    = pymunk.ShapeFilter(group=i + 1)

        space.add(torso, torso_shape)

        horse_start_angle = random.uniform(C.MIN_START_ANGLE, C.MAX_START_ANGLE)

        # Build legs
        legs = []
        for leg_index, hip_x in enumerate(HIP_POSITIONS):
            leg_length = leg_lengths[leg_index]
            hip_y      = 66.5 * C.SCALE
            hip_world  = torso.local_to_world((hip_x, hip_y))

            leg_moment = pymunk.moment_for_box(C.LEG_MASS, (C.LEG_WIDTH, leg_length))
            leg_body   = pymunk.Body(C.LEG_MASS, leg_moment)

            original_angle = -horse_start_angle if leg_index == 0 else horse_start_angle
            leg_body.angle = torso.angle + original_angle

            anchor_offset  = leg_body.local_to_world((0, -leg_length / 2))
            leg_body.position = (
                hip_world.x - anchor_offset.x,
                hip_world.y - anchor_offset.y,
            )

            leg_shape           = pymunk.Poly.create_box(leg_body, (C.LEG_WIDTH, leg_length))
            leg_shape.friction  = 2.8
            leg_shape.elasticity = 0
            leg_shape.filter    = pymunk.ShapeFilter(group=i + 1)

            hip_joint = pymunk.PivotJoint(torso, leg_body, (hip_x, hip_y), (0, -leg_length / 2))
            hip_joint.collide_bodies = False

            hip_limit = pymunk.RotaryLimitJoint(torso, leg_body, C.HIP_MIN_ANGLE, C.HIP_MAX_ANGLE)

            hip_motor = pymunk.SimpleMotor(torso, leg_body, 0)
            if leg_index == 1:
                front_leg_force    = random.uniform(C.MIN_FRONT_LEG_FORCE, C.MAX_FRONT_LEG_FORCE)
                hip_motor.max_force = front_leg_force
            else:
                front_leg_force    = None
                hip_motor.max_force = float("inf")

            space.add(leg_body, leg_shape, hip_joint, hip_limit, hip_motor)

            legs.append(Leg(
                body=leg_body,
                shape=leg_shape,
                joint=hip_joint,
                limit=hip_limit,
                motor=hip_motor,
                hip_x=hip_x,
                motor_force=front_leg_force,
                original_angle=original_angle,
                wait_time=random.uniform(C.MIN_LEG_WAIT, C.MAX_LEG_WAIT),
                move_duration=random.uniform(C.MIN_MOVE_TIME, C.MAX_MOVE_TIME),
            ))

        horses.append(RaceHorse(
            lane=i,
            torso=torso,
            color=C.HORSE_COLORS[i],
            legs=legs,
            leg_lengths=leg_lengths,
            start_angle=horse_start_angle,
        ))

    return space, horses


# ============================================================
# BETTING SCREEN
# ============================================================

def betting_screen(screen, clock, horses, note=""):
    """Interactive pre-race betting UI. Returns (lane, bet) or None."""

    global player_money

    title_font = get_font(s(40), bold=True)
    font       = get_font(s(26))
    small_font = get_font(s(20))

    number_keys = {
        pygame.K_1: 0, pygame.K_2: 1,
        pygame.K_3: 2, pygame.K_4: 3,
    }

    selected = None
    bet      = max(C.MIN_BET, min(C.BET_STEP * 5, player_money))

    panel_rect = pygame.Rect(0, 0, s(620), s(330))
    panel_rect.centerx = max(C.WIDTH // 2, s(260) + panel_rect.width // 2 + s(20))
    panel_rect.centery = C.HEIGHT // 2

    while True:
        clock.tick(C.FPS_TRACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in number_keys and number_keys[event.key] < C.LANE_COUNT:
                    selected = number_keys[event.key]
                if event.key in (pygame.K_UP, pygame.K_RIGHT, pygame.K_w, pygame.K_d):
                    bet = min(player_money, bet + C.BET_STEP)
                if event.key in (pygame.K_DOWN, pygame.K_LEFT, pygame.K_s, pygame.K_a):
                    bet = max(C.MIN_BET, bet - C.BET_STEP)
                if event.key == pygame.K_m:
                    bet = player_money
                if event.key in (pygame.K_RETURN, pygame.K_SPACE) and selected is not None:
                    return selected, bet

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for lane in range(C.LANE_COUNT):
                    if (lane_rect(lane).collidepoint(event.pos)
                            and not panel_rect.collidepoint(event.pos)):
                        selected = lane

        bet = max(C.MIN_BET, min(bet, player_money))

        draw_track(screen)
        draw_horses(screen, horses)

        if selected is not None:
            pygame.draw.rect(screen, C.GOLD, lane_rect(selected), max(2, s(4)))

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 18, 8, 225), panel.get_rect(), border_radius=s(14))
        screen.blit(panel, panel_rect.topleft)
        pygame.draw.rect(screen, C.GOLD, panel_rect, max(2, s(3)), border_radius=s(14))

        cx = panel_rect.centerx
        y  = panel_rect.top + s(18)

        def blit_centre(surf, cy_offset=0):
            nonlocal y
            screen.blit(surf, surf.get_rect(midtop=(cx, y + cy_offset)))

        blit_centre(title_font.render("PLACE YOUR BET", True, C.GOLD))
        y += s(58)
        blit_centre(font.render(f"Money: ${player_money}", True, C.WHITE))
        y += s(40)

        horse_label = (
            f"Horse: {selected + 1}" if selected is not None
            else "Horse: click a lane or press 1-4"
        )
        blit_centre(font.render(horse_label, True, C.WHITE if selected is not None else C.LOSE_RED))
        y += s(40)
        blit_centre(font.render(f"Bet: ${bet}", True, C.WHITE))
        y += s(34)
        blit_centre(small_font.render("UP / DOWN: change bet     M: bet everything", True, (200,200,190)))
        y += s(34)
        blit_centre(small_font.render(f"Pays {C.PAYOUT_ODDS} to 1: win ${bet * C.PAYOUT_ODDS} if your horse wins", True, C.GOLD))
        y += s(40)

        start_color = C.WHITE if selected is not None else (130, 130, 120)
        blit_centre(font.render("ENTER: start race     ESC: back to world", True, start_color))

        if note:
            note_surf = small_font.render(note, True, C.LOSE_RED)
            screen.blit(note_surf, note_surf.get_rect(midbottom=(cx, panel_rect.bottom - s(8))))

        pygame.display.flip()


# ============================================================
# MAIN RACE LOOP
# ============================================================

def run_track() -> None:
    """Run one full race (betting → race → result) then return."""

    global player_money

    pygame.display.set_caption("Four Horse Racing")
    screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT))
    clock  = pygame.time.Clock()

    space, horses = create_race()

    running            = True
    physics_accumulator = 0.0

    dragged_horse      = None
    drag_offset_x      = 0.0
    drag_offset_y      = 0.0
    last_drag_position = None

    winner              = None
    winner_message_time = None

    font       = get_font(s(38))
    small_font = get_font(s(22))

    note = ""
    if player_money < C.MIN_BET:
        player_money = C.STARTING_MONEY
        note = "You ran out of money - bankroll reset!"

    choice = betting_screen(screen, clock, horses, note)

    bet_horse    = None
    bet          = 0
    payout_done  = False
    result_text  = ""
    result_color = C.WHITE

    if choice is None:
        running = False
    else:
        bet_horse, bet = choice
        player_money  -= bet

    race_start_time = pygame.time.get_ticks()

    while running:
        dt = min(clock.tick(C.FPS_TRACK) / 1000, 0.033)

        mouse_x, mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and dragged_horse is None:
                for horse in reversed(horses):
                    if horse.rect().collidepoint(event.pos):
                        dragged_horse = horse
                        torso = horse.torso
                        drag_offset_x  = torso.position.x - event.pos[0]
                        drag_offset_y  = torso.position.y - event.pos[1]
                        last_drag_position = (torso.position.x, torso.position.y)
                        torso.velocity = (0, 0)
                        torso.angular_velocity = 0
                        for leg in horse.legs:
                            leg.body.velocity = (0, 0)
                            leg.body.angular_velocity = 0
                        physics_accumulator = 0
                        break

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and dragged_horse is not None:
                torso = dragged_horse.torso
                torso.velocity = (0, 0)
                torso.angular_velocity = 0
                for leg in dragged_horse.legs:
                    leg.body.velocity = (0, 0)
                    leg.body.angular_velocity = 0
                    leg.stop()
                    space.reindex_shapes_for_body(leg.body)
                space.reindex_shapes_for_body(torso)
                dragged_horse      = None
                last_drag_position = None
                physics_accumulator = 0

        # Drag update
        if dragged_horse is not None and winner is None:
            torso    = dragged_horse.torso
            target_x = mouse_x + drag_offset_x
            target_y = mouse_y + drag_offset_y
            old_x, old_y = last_drag_position
            dx = target_x - old_x
            dy = target_y - old_y

            torso.position = (target_x, target_y)
            torso.velocity = (0, 0)
            torso.angular_velocity = 0
            space.reindex_shapes_for_body(torso)

            for leg in dragged_horse.legs:
                leg.body.position = (leg.body.position.x + dx, leg.body.position.y + dy)
                leg.body.velocity = (0, 0)
                leg.body.angular_velocity = 0
                leg.stop()
                space.reindex_shapes_for_body(leg.body)

            last_drag_position = (target_x, target_y)

        # Update horses
        if winner is None:
            for horse in horses:
                horse.update(dt, is_dragged=(horse is dragged_horse))

        # Physics step
        if winner is None:
            physics_accumulator += dt
            while physics_accumulator >= C.PHYSICS_STEP:
                space.step(C.PHYSICS_STEP)
                physics_accumulator -= C.PHYSICS_STEP

            # Finish-line detection
            for horse in horses:
                if horse.rect().right >= C.FINISH_X:
                    winner              = horse.lane
                    winner_message_time = pygame.time.get_ticks()
                    break

            # Timeout
            if winner is None and pygame.time.get_ticks() - race_start_time >= C.MAX_RACE_TIME:
                best_x    = -1
                best_lane = 0
                for horse in horses:
                    if horse.rect().right > best_x:
                        best_x    = horse.rect().right
                        best_lane = horse.lane
                winner              = best_lane
                winner_message_time = pygame.time.get_ticks()

        # Draw
        draw_track(screen, bet_info=(bet_horse, bet) if choice is not None else None)
        draw_horses(screen, horses)

        if winner is not None:
            if not payout_done:
                payout_done = True
                if winner == bet_horse:
                    winnings      = bet * C.PAYOUT_ODDS
                    player_money += bet + winnings
                    result_text   = f"Horse {winner + 1} wins! You won ${winnings}!"
                    result_color  = C.GOLD
                else:
                    result_text  = f"Horse {winner + 1} wins! You lost your ${bet} bet."
                    result_color = C.LOSE_RED

            banner_rect = pygame.Rect(0, 0, s(700), s(110))
            banner_rect.center = (C.WIDTH // 2, C.HEIGHT // 2)

            banner = pygame.Surface(banner_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(banner, (20, 18, 8, 235), banner.get_rect(), border_radius=s(14))
            screen.blit(banner, banner_rect.topleft)
            pygame.draw.rect(screen, C.GOLD, banner_rect, max(2, s(3)), border_radius=s(14))

            cx = banner_rect.centerx
            y  = banner_rect.top + s(18)

            msg = font.render(result_text, True, result_color)
            screen.blit(msg, msg.get_rect(midtop=(cx, y)))
            y += s(50)
            sub = small_font.render("Press any key or click to return to world", True, C.WHITE)
            screen.blit(sub, sub.get_rect(midtop=(cx, y)))

            if pygame.time.get_ticks() - winner_message_time > 800:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); raise SystemExit
                    if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                        running = False
            else:
                pygame.event.clear()

        pygame.display.flip()
