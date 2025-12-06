import pygame
import time
import math
from utils import scale_image, blit_rotate_center
import os
import random

pygame.init()         
pygame.font.init() 

GRASS = scale_image(pygame.image.load("imgs/grass.jpg"), 2.5)
TRACK = scale_image(pygame.image.load("imgs/track.png"), 0.9)
TRACK_BORDER = scale_image(pygame.image.load("imgs/track-border.png"), 0.9)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

FINISH = pygame.image.load("imgs/finish.png")
FINISH_MASK = pygame.mask.from_surface(FINISH)
FINISH_POSITION = (130, 250)

RED_CAR = scale_image(pygame.image.load("imgs/red-car.png"), 0.55)
GREEN_CAR = scale_image(pygame.image.load("imgs/green-car.png"), 0.55)  # AI CAR

WIDTH, HEIGHT = TRACK.get_width(), TRACK.get_height()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Car Racing Game")

FPS = 60

SOUND_DIR = "imgs"  

def load_sound(name, volume=1.0):
    path = os.path.join(SOUND_DIR, name)
    try:
        s = pygame.mixer.Sound(path)
        s.set_volume(volume)
        return s
    except Exception as e:
        print(f"[sound] could not load {path}: {e}")
        return None

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()
ENGINE_SOUND = load_sound("engine.wav", volume=0.25)
CRASH_SOUND = load_sound("crash.wav", volume=0.6)
FINISH_SOUND = load_sound("finish.wav", volume=0.5)
HORN_SOUND = load_sound("horn.wav", volume=0.6)
NEW_AI_SOUND = load_sound("horn.wav", volume=0.3)  # Reuse horn sound or add new sound

ENGINE_CHANNEL = pygame.mixer.Channel(1) if pygame.mixer.get_init() else None


class AbstractCar:
    def __init__(self, max_vel, rotation_vel):
        self.img = self.IMG
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        self.acceleration = 0.1
        self.crash_cooldown = 0
        self.active = True  # Whether the car is active/visible

    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel

    def draw(self, win):
        if self.active:
            blit_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        if self.active:
            self.vel = min(self.vel + self.acceleration, self.max_vel)
            self.move()

    def move_backward(self):
        if self.active:
            self.vel = max(self.vel - self.acceleration, -self.max_vel / 2)
            self.move()

    def move(self):
        if not self.active:
            return
            
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel

        self.y -= vertical
        self.x -= horizontal

    def reduce_speed(self):
        if self.active:
            self.vel = max(self.vel - self.acceleration / 3, 0)
            self.move()

    def collide(self, mask, x=0, y=0):
        if not self.active:
            return None
            
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        poi = mask.overlap(car_mask, offset)
        return poi

    def bounce(self):
        if not self.active:
            return
            
        self.vel = -self.vel / 2
        self.angle += 30 if self.vel > 0 else -30
        self.move()
        self.crash_cooldown = 10

    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0
        self.crash_cooldown = 0
        self.active = True

    def deactivate(self):
        """Deactivate the car (remove from screen)"""
        self.active = False
        self.vel = 0

    def update_cooldown(self):
        if self.crash_cooldown > 0:
            self.crash_cooldown -= 1


class PlayerCar(AbstractCar):
    IMG = RED_CAR
    START_POS = (180, 200)


class AICar(AbstractCar):
    IMG = GREEN_CAR
    START_POS = (150, 220)

    def __init__(self, max_vel, rotation_vel):
        super().__init__(max_vel, rotation_vel)

        # Define multiple possible paths for variety
        self.paths = [
            # Path 1: Standard racing line
            [
                (180, 120), (220, 120), (260, 120), (310, 120), (350, 150),
                (390, 190), (420, 220), (420, 260), (410, 300), (410, 340),
                (380, 380), (330, 410), (280, 430), (230, 430), (200, 420),
                (170, 400), (150, 370), (150, 350), (140, 320), (140, 280),
                (145, 250), (150, 220), (160, 200), (170, 180)
            ],
            # Path 2: Slightly different line
            [
                (170, 120), (210, 125), (250, 130), (300, 135), (340, 160),
                (380, 200), (415, 230), (415, 270), (405, 310), (400, 350),
                (370, 390), (320, 420), (270, 425), (220, 425), (190, 415),
                (160, 390), (145, 360), (145, 330), (135, 300), (135, 260),
                (140, 230), (150, 200), (165, 180), (175, 160)
            ],
            # Path 3: More aggressive line
            [
                (190, 120), (230, 115), (270, 115), (320, 115), (360, 140),
                (400, 180), (425, 210), (425, 250), (415, 290), (415, 330),
                (390, 370), (340, 400), (290, 420), (240, 420), (210, 410),
                (180, 385), (160, 355), (160, 325), (150, 295), (150, 255),
                (155, 225), (165, 195), (180, 175), (190, 155)
            ]
        ]
        
        # Randomly select a path for this AI instance
        self.path = random.choice(self.paths)
        self.target_index = 0
        self.crash_count = 0
        self.max_crashes = 3  # After 3 crashes, this AI car is removed

    def follow_path(self):
        if not self.active:
            return
            
        self.update_cooldown()
        
        if self.crash_cooldown > 0:
            self.reduce_speed()
            return
        
        if self.target_index >= len(self.path):
            self.target_index = 0

        tx, ty = self.path[self.target_index]
        dx = tx - self.x
        dy = ty - self.y
        
        distance = math.sqrt(dx**2 + dy**2)
        angle_to_target = math.degrees(math.atan2(dx, -dy))
        
        angle_difference = (angle_to_target - self.angle) % 360
        if angle_difference > 180:
            angle_difference -= 360

        # Smart steering
        if abs(angle_difference) > 5:
            if angle_difference > 0:
                self.rotate(left=True)
            else:
                self.rotate(right=True)
        
        # Adaptive speed control
        if abs(angle_difference) > 45:
            self.vel = max(self.vel - self.acceleration * 1.2, self.max_vel * 0.4)
        elif distance < 30:
            self.vel = max(self.vel - self.acceleration * 0.5, self.max_vel * 0.7)
        else:
            self.move_forward()
        
        if distance < 25:
            self.target_index += 1
            if self.target_index >= len(self.path):
                self.target_index = 0
    
    def handle_collision(self):
        """Handle collision and return True if car should be removed"""
        if not self.active or self.crash_cooldown > 0:
            return False
            
        if self.collide(TRACK_BORDER_MASK) is not None:
            # Play crash sound
            if CRASH_SOUND:
                CRASH_SOUND.play()
            
            # Increment crash count
            self.crash_count += 1
            
            # Bounce effect
            self.vel = -self.vel / 3
            self.angle += 45
            self.move()
            self.crash_cooldown = 15
            
            # Reset to a previous checkpoint
            self.target_index = max(0, self.target_index - 3)
            
            # If crashed too many times, mark for removal
            if self.crash_count >= self.max_crashes:
                return True
                
        return False


def draw(win, images, cars, lap, start_time, ai_respawn_timer, ai_cars_count):
    for img, pos in images:
        win.blit(img, pos)

    # Draw only active cars
    for car in cars:
        if car.active:
            car.draw(win)

    # UI
    elapsed = int(time.time() - start_time)
    speed = int(cars[0].vel * 10)

    font = pygame.font.Font(None, 26)
    font_large = pygame.font.Font(None, 36)

    ui_text = [
        f"Lap : {lap}",
        f"Speed : {speed} km/h",
        f"Time : {elapsed}s",
        f"AI Cars : {ai_cars_count}",
        "Controls : W A S D | H = Horn | R = Restart"
    ]

    y = 10
    for t in ui_text:
        label = font.render(t, True, (255, 255, 255))
        win.blit(label, (10, y))
        y += 25

    # Show respawn timer if active
    if ai_respawn_timer > 0:
        respawn_text = font_large.render(f"New AI in: {ai_respawn_timer//60 + 1}", True, (255, 255, 0))
        win.blit(respawn_text, (WIDTH // 2 - 80, 50))

    pygame.display.update()


def move_player(player):
    keys = pygame.key.get_pressed()
    moved = False

    if keys[pygame.K_a]:
        player.rotate(left=True)
    if keys[pygame.K_d]:
        player.rotate(right=True)

    if keys[pygame.K_w]:
        moved = True
        player.move_forward()

    if keys[pygame.K_s]:
        moved = True
        player.move_backward()

    if not moved:
        player.reduce_speed()

    return moved


def update_engine_sound(is_moving, speed):
    if ENGINE_SOUND is None or ENGINE_CHANNEL is None:
        return

    try:
        if is_moving and not ENGINE_CHANNEL.get_busy():
            ENGINE_CHANNEL.play(ENGINE_SOUND, loops=-1)
        if not is_moving and ENGINE_CHANNEL.get_busy():
            ENGINE_CHANNEL.fadeout(400)
        
        vol = max(0.12, min(0.8, 0.12 + (abs(speed) / 20.0)))
        ENGINE_CHANNEL.set_volume(vol * 0.9)
    except Exception as e:
        print("[sound] engine update error", e)


def create_new_ai_car():
    """Create a new AI car with random characteristics"""
    # Randomize AI characteristics for variety
    max_vel = random.uniform(5.5, 6.5)  # Slightly different speeds
    rotation_vel = random.uniform(3.5, 4.5)  # Slightly different turning
    
    new_ai = AICar(max_vel, rotation_vel)
    
    # Random starting position near the original
    start_x = random.randint(140, 160)
    start_y = random.randint(210, 230)
    new_ai.START_POS = (start_x, start_y)
    new_ai.x, new_ai.y = new_ai.START_POS
    
    return new_ai


# Main game loop
run = True
clock = pygame.time.Clock()
images = [(GRASS, (0, 0)), (TRACK, (0, 0)), (FINISH, FINISH_POSITION), (TRACK_BORDER, (0, 0))]

player_car = PlayerCar(8, 8)
ai_cars = [AICar(6, 4)]  # Start with one AI car
all_cars = [player_car] + ai_cars

lap = 1
start_time = time.time()
ai_respawn_timer = 0
ai_cars_count = len(ai_cars)
ai_cars_removed = 0
ai_cars_spawned = 1

while run:
    clock.tick(FPS)
    
    # Draw everything
    draw(WIN, images, all_cars, lap, start_time, ai_respawn_timer, ai_cars_count)

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                player_car.reset()
                # Reset all AI cars
                for ai in ai_cars:
                    ai.reset()
                lap = 1
                start_time = time.time()
                ai_respawn_timer = 0
            if event.key == pygame.K_h:
                if HORN_SOUND:
                    HORN_SOUND.play()

    # Update player
    moving = move_player(player_car)
    update_engine_sound(moving, player_car.vel)
    
    # Update AI cars
    ai_cars_to_remove = []
    for ai_car in ai_cars:
        if ai_car.active:
            ai_car.follow_path()
            
            # Check for collision
            if ai_car.handle_collision():
                # Mark for removal if crashed too many times
                ai_car.deactivate()
                ai_respawn_timer = 180  # 3 seconds at 60 FPS
                ai_cars_removed += 1
                
                # Play removal sound
                if CRASH_SOUND:
                    CRASH_SOUND.play()
    
    # Remove inactive AI cars
    ai_cars = [ai for ai in ai_cars if ai.active]
    
    # Handle AI respawn
    if ai_respawn_timer > 0:
        ai_respawn_timer -= 1
        if ai_respawn_timer == 0:
            # Spawn new AI car
            new_ai = create_new_ai_car()
            ai_cars.append(new_ai)
            ai_cars_spawned += 1
            
            # Play spawn sound
            if NEW_AI_SOUND:
                NEW_AI_SOUND.play()
    
    # Update all cars list
    all_cars = [player_car] + ai_cars
    ai_cars_count = len(ai_cars)
    
    # Check collisions for player
    if player_car.collide(TRACK_BORDER_MASK) is not None:
        if CRASH_SOUND:
            CRASH_SOUND.play()
        player_car.bounce()
    
    # Check finish line
    finish_collision = player_car.collide(FINISH_MASK, *FINISH_POSITION)
    if finish_collision:
        if finish_collision[1] > 0:
            player_car.reset()
            # Reset all AI cars on new lap
            for ai in ai_cars:
                ai.reset()
            lap += 1
            if FINISH_SOUND:
                FINISH_SOUND.play()

pygame.quit()