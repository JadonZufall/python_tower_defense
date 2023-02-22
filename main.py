from collections import defaultdict
import pygame
import random
pygame.init()
window = pygame.display.set_mode((2_000, 1_000))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 25, True, False)
is_running = True

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

camera_x = 0
camera_y = 0
camera_dragging = False

DEFAULT_DEBOUNCE_TIME = 500
debounce: defaultdict[int, dict[str, int]] = defaultdict(lambda: {"released": True, "time": 0, "dt": DEFAULT_DEBOUNCE_TIME})

DEBUG_MOUSE_HOVER_IMG = pygame.Surface((50, 50), pygame.SRCALPHA)
DEBUG_MOUSE_HOVER_IMG.fill((255, 0, 0, 100))
mouse_hover_img = None

debug_draw_zero_dot = True

DEFAULT_DEBUG_X = 15
DEFAULT_DEBUG_Y = 15
debug_x = 15
debug_y = 15
future_debug_y = 0

entity_ids = 0
pylons: list["Pylon"] = []
zombies: list["Zombie"] = []

def distance(x1, y1, x2, y2) -> float:
    return ((x1 - x2)**2 + (y1 - y2)**2) ** 0.5

def rel_pos(pos: tuple[int, int]) -> tuple[int, int]:
    return pos[0] + (camera_x + window.get_width() // 2), pos[1] + (camera_y + window.get_height() // 2)

def real_pos(pos: tuple[int, int]) -> tuple[int, int]:
    return pos[0] - (camera_x + window.get_width() // 2), pos[1] - (camera_y + window.get_height() // 2)


def debug_col(text: str) -> None:
    global debug_x, debug_y, future_debug_y
    txt = font.render(text, True, WHITE, BLACK)
    window.blit(txt, (debug_x, debug_y))
    future_debug_y = txt.get_height() if txt.get_height() > future_debug_y else future_debug_y
    debug_x += txt.get_width()

def debug_row(text: str) -> None:
    global debug_x, debug_y, future_debug_y
    debug_x = DEFAULT_DEBUG_X
    debug_y += future_debug_y
    txt = font.render(text, True, WHITE, BLACK)
    window.blit(txt, (debug_x, debug_y))
    debug_x += txt.get_width()
    future_debug_y = txt.get_height()

def toggle_debug_mouse_hover_img() -> None:
    global mouse_hover_img
    if mouse_hover_img is None:
        mouse_hover_img = DEBUG_MOUSE_HOVER_IMG
    else:
        mouse_hover_img = None


ZOMBIE_IMG = pygame.Surface((50, 50), pygame.SRCALPHA)
pygame.draw.circle(ZOMBIE_IMG, (0, 150, 0), (25, 25), 25)

ZOMBIE_HP = pygame.Surface((50, 10), pygame.SRCALPHA)
ZOMBIE_HP.fill(RED)

class Zombie:
    def __init__(self, x: int, y: int) -> None:
        global zombies
        global entity_ids
        self.hp = 100
        self.mhp = 100
        zombies.append(self)
        self.x, self.y = x, y
        self.target = (0, 0)
        self.velocity = 1000
        self.render_hp = True
        self.hp_bar = pygame.Surface((ZOMBIE_IMG.get_width(), 10), pygame.SRCALPHA)
        self.hp_bar.fill(RED)
        self.id = entity_ids
        entity_ids += 1
    
    def redraw_hp_bar(self) -> None:
        try:
            self.hp_bar = pygame.Surface((ZOMBIE_IMG.get_width() * self.hp / self.mhp, 10), pygame.SRCALPHA)
            self.hp_bar.fill(RED)
        except pygame.error:
            self.hp_bar = pygame.Surface((1, 10), pygame.SRCALPHA)
            self.hp_bar.fill(RED)


    def damage(self, amount: int) -> None:
        self.hp -= amount

    def update(self, dt: int) -> None:
        if self.hp <= 0:
            zombies.remove(self)
            return None
        d = distance(self.x, self.y, self.target[0], self.target[1])
        if d < 0.3:
            self.x, self.y = self.target
        if abs(d) != 0 and d != 0:
            dx = ((self.target[0] - self.x) / abs(d))
            dy = ((self.target[1] - self.y) / abs(d))
        else:
            dx = 0
            dy = 0
        # TODO: Need some collision detection here!
        self.x += (self.velocity * dx) * (dt / (1_000 * 60))
        self.y += (self.velocity * dy) * (dt / (1_000 * 60))
        print(f"x={self.x} y={self.y}")

    def render(self) -> None:
        window.blit(ZOMBIE_IMG, rel_pos((self.x - ZOMBIE_IMG.get_width() // 2, self.y - ZOMBIE_IMG.get_height() // 2)))
        if self.render_hp:
            self.redraw_hp_bar()
            window.blit(self.hp_bar, rel_pos((self.x - self.hp_bar.get_width() // 2, self.y + ZOMBIE_IMG.get_height() // 2 + ZOMBIE_HP.get_height())))


PYLON_IMG = pygame.Surface((100, 100), pygame.SRCALPHA)
pygame.draw.circle(PYLON_IMG, (0, 255, 255), (50, 50), 50, 10)

PYLON_RANGE = pygame.Surface((500, 500), pygame.SRCALPHA)
pygame.draw.circle(PYLON_RANGE, (100, 100, 100, 100), (250, 250), 250)

class Pylon:
    def __init__(self, x: int, y: int) -> None:
        global pylons
        global entity_ids
        pylons.append(self)
        self.x, self.y = x, y
        self.range = 250
        self.show_range = False
        self.cooldown = 0
        self.damage = 10
        self.shoot_x, self.shoot_y = 0, 0
        self.id = entity_ids
        entity_ids += 1

    def update(self, dt: int) -> None:
        if not self.cooldown <= 0:
            self.cooldown -= dt
            return None

        zombies_in_range = []
        for zombie in zombies:
            d = distance(self.x, self.y, zombie.x, zombie.y)
            if d < self.range:
                zombies_in_range.append((zombie, d))
        
        if len(zombies_in_range) == 0:
            return None

        closest_zombie = min(zombies_in_range, key=lambda x: x[1])[0]
        self.shoot_x, self.shoot_y = closest_zombie.x, closest_zombie.y
        closest_zombie.damage(self.damage)
        self.cooldown = 1_000

    def render(self) -> None:
        if self.show_range:
            window.blit(PYLON_RANGE, rel_pos((self.x - PYLON_RANGE.get_width() // 2, self.y - PYLON_RANGE.get_height() // 2)))
        window.blit(PYLON_IMG, rel_pos((self.x - PYLON_IMG.get_width() // 2, self.y - PYLON_IMG.get_height() // 2)))
        if self.cooldown >= 800:
            pygame.draw.line(window, (255, 0, 0), rel_pos((self.x, self.y)), rel_pos((self.shoot_x, self.shoot_y)), width=3)


random_zombie_spawn_cooldown = 0
def spawn_zombie_randomly() -> None:
    roll = random.randint(0, 3)
    if roll == 0:
        y = 0
        x = window.get_width() // 2
    elif roll == 1:
        y = 0
        x = -1 * window.get_width() // 2
    elif roll == 2:
        y = window.get_height() // 2
        x = 0
    elif roll == 3:
        y = -1 * window.get_height() // 2
        x = 0
    else:
        raise Exception("Wtf?")
    Zombie(x, y)


while is_running:
    debug_x, debug_y = DEFAULT_DEBUG_X, DEFAULT_DEBUG_Y
    future_debug_y = 0
    clock.tick(60)
    dt = clock.get_time()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False
    
    if random_zombie_spawn_cooldown <= 0:
        random_zombie_spawn_cooldown = 1_000
        spawn_zombie_randomly()
    else:
        random_zombie_spawn_cooldown -= dt
    
    mouse = pygame.mouse.get_pressed(num_buttons=3)
    mouse_pos = pygame.mouse.get_pos()
    mouse_delta = pygame.mouse.get_rel()
    if camera_dragging:
        camera_x += int(mouse_delta[0] * 1.25)
        camera_y += int(mouse_delta[1] * 1.25)
    
    if mouse[1]:
        camera_dragging = True
    else:
        camera_dragging = False
    
    if mouse[0] and mouse_hover_img is PYLON_IMG:
        Pylon(*real_pos((mouse_pos[0] + PYLON_IMG.get_width() // 2, mouse_pos[1] + PYLON_IMG.get_height() // 2)))
        mouse_hover_img = None
    
    elif mouse[0] and mouse_hover_img is ZOMBIE_IMG:
        Zombie(*real_pos((mouse_pos[0] + ZOMBIE_IMG.get_width() // 2, mouse_pos[1] + ZOMBIE_IMG.get_height() // 2)))
        mouse_hover_img = None

    elif mouse[0]:
        for pylon in pylons:
            if distance(*real_pos(mouse_pos), pylon.x, pylon.y) < PYLON_IMG.get_width() // 2:
                pylon.show_range = True
    
    if mouse[2] and mouse_hover_img is not None:
        mouse_hover_img = None
    
    elif mouse[2] and not mouse[1]:
        for pylon in pylons:
            if distance(*real_pos(mouse_pos), pylon.x, pylon.y) < PYLON_IMG.get_width():
                pylon.show_range = False
    
    


    keys = pygame.key.get_pressed()
    if keys[pygame.K_F1] and debounce[58]["released"] and debounce[58]["time"] <= 0:
        toggle_debug_mouse_hover_img()

    if keys[pygame.K_F2] and debounce[59]["released"] and debounce[59]["time"] <= 0:
        debug_draw_zero_dot = not debug_draw_zero_dot
    
    if keys[pygame.K_p] and debounce[19]["released"] and debounce[19]["time"] <= 0:
        mouse_hover_img = PYLON_IMG
    
    elif keys[pygame.K_z] and debounce[29]["released"] and debounce[29]["time"] <= 0:
        mouse_hover_img = ZOMBIE_IMG

    elif keys[pygame.K_c] and debounce[6]["released"] and debounce[6]["time"] <= 0:
        zombies = []

    for key, is_pressed in enumerate(keys):
        if is_pressed:
            print(key)
            #print(debounce[key])
        if is_pressed and debounce[key]["released"]:
            debounce[key]["released"] = False
            debounce[key]["time"] = debounce[key]["dt"]
        if not is_pressed and not debounce[key]["released"] and debounce[key]["time"] <= 0:
            debounce[key]["released"] = True
        debounce[key]["time"] = debounce[key]["time"] - dt
        if debounce[key]["time"] <= 0:
            debounce[key]["time"] = 0  

    window.fill((255, 255, 255))

    for pylon in pylons:
        pylon.update(dt)
        pylon.render()
    
    for zombie in zombies:
        zombie.update(dt)
        zombie.render()

    debug_row(f" [DEBUG] ")
    debug_x += 5
    if debug_draw_zero_dot:
        pygame.draw.circle(window, (255, 0, 0), rel_pos((0, 0)), 5)
        debug_col(f" [CDOT] ")
        debug_x += 5
    if mouse_hover_img == DEBUG_MOUSE_HOVER_IMG:
        debug_col(f" [MHOV] ")
        debug_x += 5

    debug_row(f"camera_x = {'+' if camera_x >= 0 else '-'}{abs(camera_x):0>6}")
    fvalue = f"{abs(mouse_delta[0]):0>3}"
    fstring = f"{'+' if mouse_delta[0] >= 0 else '-'}{fvalue}"
    debug_col(f"{fstring}")

    debug_row(f"camera_y = {'+' if camera_y >= 0 else '-'}{abs(camera_y):0>6}")

    fvalue = f"{abs(mouse_delta[1]):0>3}"
    fstring = f"{'+' if mouse_delta[1] >= 0 else '-'}{fvalue}"
    debug_col(f"{fstring}")
    
    debug_row(f"mouse = {mouse}")
    debug_row(f"dt = {dt}")

    if mouse_hover_img is not None:
        window.blit(mouse_hover_img, mouse_pos)
    pygame.display.flip()
    
