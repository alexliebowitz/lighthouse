import pygame
import math
import random

from pygame.locals import *
from constants import *


pygame.init()
pygame.mixer.init()
 
mainfont = pygame.font.SysFont('Helvetica', 25)

mainsurf = pygame.display.set_mode((WIDTH, HEIGHT))

rocketspeed = 1

boostmode = False
boostleft = MAX_BOOST

devils = []
bombs = []
timebomb = None

level = 1

paused = False
gamewon = False
gamelost = False

devilgroup = pygame.sprite.Group()

winsound = pygame.mixer.Sound("sounds/winscreen.wav")
losesound = pygame.mixer.Sound("sounds/sadtrombone.wav")
levelupsound = pygame.mixer.Sound("sounds/omnomnom.ogg")


def randomdirection(maxdist=10):
    # Return a vector we can use to push an object in a random
    # direction. For example, if we return (-5, -5), that means
    # push the object 5 pixels up and to the left.

    # We're going to pick a random point around a unit circle.
    # First, we need to pick a number from -1 to 1 to choose
    # where to sample from the circle along the x dimension.

    x = random.uniform(-1, 1)

    # Use the circle formula to get the y position of the circle
    # for this value of x.
    y = math.sqrt(1 - x**2)

    # Now for any x dimension, there are actually *2* possible
    # points along the y dimension: the top or the bottom.
    # math.sqrt only returns a positive number, so randomly
    # flip y to the bottom 50% of the time.
    if random.choice([True, False]):
        y *= -1

    distance = random.randint(0, maxdist)

    return (x * distance, y * distance)

class Screen(pygame.sprite.Sprite):
    BACKDROP_COLOR = None
    BACKDROP_ALPHA = 60
    CONTENT_COLOR = None

    _snapshot = None
    _backdrop = None
    _content = None

    def __init__(self):
        super().__init__()

        self.image = pygame.Surface((WIDTH, HEIGHT))

        self._snapshot = mainsurf.copy()

        self._backdrop = pygame.Surface((WIDTH, HEIGHT))
        self._backdrop.fill(self.BACKDROP_COLOR)
        self._backdrop.set_alpha(self.BACKDROP_ALPHA)

        self._content = pygame.Surface((WIDTH, HEIGHT))
        self._content.set_colorkey((0, 0, 0))

    def draw(self):
        self.image.blit(self._snapshot, (0, 0))
        self.image.blit(self._backdrop, (0, 0))
        self.image.blit(self._content, (0, 0))
        mainsurf.blit(self.image, (0, 0))

class WinScreen(Screen):
    BACKDROP_COLOR = (255, 255, 255)
    BACKDROP_ALPHA = 255
    CONTENT_COLOR = (0, 100, 0)

    def draw(self):
        textsurf = mainfont.render('YOU WON', True, self.CONTENT_COLOR)
        textrect = textsurf.get_rect(center=mainsurf.get_rect().center)

        self._content.blit(textsurf, textrect)
        super().draw()

class LoseScreen(Screen):
    BACKDROP_COLOR = (150, 0, 0)
    CONTENT_COLOR = (230, 230, 230)

    def draw(self):
        textsurf = mainfont.render("YOU LOST", True, self.CONTENT_COLOR)
        textrect = textsurf.get_rect(center=mainsurf.get_rect().center)

        self._content.blit(textsurf, textrect)
        super().draw()

class PauseScreen(Screen):
    BACKDROP_COLOR = (252, 254, 234)
    CONTENT_COLOR = (0, 0, 0)

    def draw(self):
        textsurf = mainfont.render("GAME PAUSED", True, self.CONTENT_COLOR)
        textrect = textsurf.get_rect(center=mainsurf.get_rect().center)

        self._content.blit(textsurf, textrect)
        super().draw()


class Rocket(pygame.sprite.Sprite):
    _frames = None
    _trail = None

    def __init__(self):
        super().__init__()

        self._frames = 0
        self._trail = []

        self.image = pygame.image.load("images/rocket.png")
        self.rect = pygame.rect.Rect((WIDTH / 2, HEIGHT / 2), self.image.get_size())

    def draw_trail_rocket(self, coords, alpha):
        tempsurf = pygame.Surface((self.rect.width, self.rect.height))
        tempsurf.set_colorkey((0, 0, 0))
        tempsurf.blit(self.image, (0, 0))
        tempsurf.set_alpha(alpha)

        mainsurf.blit(tempsurf, coords)

    def draw(self):
        self._frames += 1

        # Compute new trail and blit it
        if self._frames % ROCKET_TRAIL_SPACING == 0:
            self._trail.insert(0, (self.rect.x, self.rect.y))

        if len(self._trail) > ROCKET_MAX_TRAIL:
            self._trail = self._trail[:-1]


        alpha = ROCKET_TRAIL_START_ALPHA
        for trailcoord in self._trail:
            alpha *= ROCKET_TRAIL_FADE

            self.draw_trail_rocket(trailcoord, alpha)

        # Blit rocket

        mainsurf.blit(self.image, self.rect)

class Shield(pygame.sprite.Sprite):
    _frames = None
    _rocket = None
    radius = None
    done = None

    def __init__(self, rocket):
        super().__init__()

        self._frames = 0
        self.radius = 0
        self._rocket = rocket
        self.done = False

        # We set the self.rect to to match the rocket's rectangle.
        # Height and width don't matter, because as long as we
        # provide a .radius, Pygame will use that for collision
        # detection.
        self.rect = rocket.rect.copy()

        self._circlesurf = pygame.Surface((WIDTH, HEIGHT))
        self._circlesurf.set_alpha(SHIELD_ALPHA)
        self._circlesurf.set_colorkey((0, 0, 0))

    def draw(self):
        self._frames += 1
        if self._frames <= SHIELD_DURATION:
            if self.radius <= SHIELD_MAX:
                self.radius += SHIELD_SPEED
        else:  # We are past the duration, so shrink the field
            self.radius -= SHIELD_SPEED
            if self.radius <= 0:
                self.done = True
                return

        self.rect.centerx = self._rocket.rect.centerx
        self.rect.centery = self._rocket.rect.centery

        self._circlesurf.fill((0, 0, 0))

        pygame.draw.circle(self._circlesurf, SHIELD_COLOR,
                           (self._rocket.rect.centerx, self._rocket.rect.centery), self.radius)
        mainsurf.blit(self._circlesurf, (0, 0))

class Devil(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()

        self.image = pygame.image.load("images/devil.png")

        side = random.randint(0, 3)
        if side == 0:  # Top
            x = random.randint(0, WIDTH)
            y = 0
        elif side == 1:  # Right
            x = WIDTH
            y = random.randint(0, HEIGHT)
        elif side == 2:  # Bottom
            x = random.randint(0, WIDTH)
            y = HEIGHT
        elif side == 3:  # Left
            x = 0
            y = random.randint(0, HEIGHT)

        self.rect = pygame.rect.Rect((x, y), self.image.get_size())

        devilgroup.add(self)

    def draw(self):
        mainsurf.blit(self.image, self.rect)

class BossDevil(Devil):
    def __init__(self):
        super().__init__()

        self._normalimage = pygame.image.load("images/boss.png")
        self._invertedimage = pygame.image.load("images/boss2.png")

        self._framecounter = 0
        self._inverted = False

        self.image = pygame.image.load('images/boss.png')
        self.rect = pygame.rect.Rect((WIDTH / 2, HEIGHT / 2), self.image.get_size())

        devilgroup.add(self)

    def draw(self):
        self._framecounter += 1

        if self._framecounter == 5:
            self._framecounter = 0
            self._inverted = not self._inverted
            if self._inverted:
                self.image = self._invertedimage
            else:
                self.image = self._normalimage

        mainsurf.blit(self.image, self.rect)

class Item(pygame.sprite.Sprite):
    IMAGE_FILE = None

    def __init__(self):
        super().__init__()

        self.image = pygame.image.load("images/" + self.IMAGE_FILE)
        self.rect = pygame.rect.Rect((random.randint(15, WIDTH - 15), random.randint(15, HEIGHT - 15)), self.image.get_size())


    def draw(self):
        mainsurf.blit(self.image, self.rect)


class Cookie(Item):
    IMAGE_FILE = "cookie.png"


class Powerup(Item):
    SOUND_FILE = "powerup.wav"
    NAME = None
    BLINK_RATE = 3

    state = None
    _sound = None
    _frames = None
    _blinker = None

    def __init__(self):
        super().__init__()

        self._sound = pygame.mixer.Sound("sounds/" + self.SOUND_FILE)
        self.state = 'notdropped'
        self._frames = 0
        self._blinker = 0

    def drop(self):
        self.state = 'onscreen'

    def collect(self):
        self.state = 'collected'
        self._sound.play()

    def draw(self):
        self._frames += 1

        if self._frames <= 30:
            if self._frames % self.BLINK_RATE == 0:
                self._blinker = not self._blinker

            if self._blinker:
                mainsurf.blit(self.image, self.rect)
        else:
            mainsurf.blit(self.image, self.rect)



class BombPowerup(Powerup):
    IMAGE_FILE = "bomb_powerup.png"
    NAME = 'bomb'

class ShieldPowerup(Powerup):
    IMAGE_FILE = "shield_powerup.png"
    NAME = 'shield'

class TimeBombPowerup(Powerup):
    IMAGE_FILE = "time_bomb_powerup.png"
    NAME = 'timebomb'



class Bomb(pygame.sprite.Sprite):
    BLAST_RADIUS = 300
    EXPLOSION_COLOR_1 = (255, 255, 255)
    EXPLOSION_COLOR_2 = (200, 200, 200)
    GROW_RATE = 10
    FUSE = 100

    _frames = None
    _blinker = None
    _frames_since_detonated = None
    _circlesurf = None

    radius = None
    exploding = None
    done = None

    def __init__(self, x, y):
        super().__init__()

        self._frames = 0
        self._blinker = False
        self.radius = 0
        self.exploding = False
        self.done = False
        self._circlesurf = pygame.Surface((WIDTH, HEIGHT))
        self._circlesurf.set_colorkey((0, 0, 0))

        self.image = pygame.image.load("images/bomb.png")
        self.rect = pygame.rect.Rect((x, y), self.image.get_size())

    def _get_alpha(self):
        # ratio_done is how far along we are in the explosion.
        # For example, if we're 50% done, then ratio_done will be 0.5.
        ratio_done = self.radius / self.BLAST_RADIUS

        # Start at 255 (no transparency) and then fade out to 0
        return 255 * (1 - ratio_done)

    def detonate(self):
        self.exploding = True
        self._frames_since_detonated = 0

    def draw(self):
        self._frames += 1
        if self.exploding:
            self._frames_since_detonated += 1

        if self._frames == self.FUSE and not self.exploding:  # At the 100 frame mark, we detonate
            self.detonate()

        if not self.exploding:
            # We haven't exploded yet, so draw the normal bomb
            mainsurf.blit(self.image, self.rect)
        elif self.radius <= self.BLAST_RADIUS:  # Exploding
            self._frames_since_detonated += 1
            if self._frames_since_detonated % 3 == 0:  # Every third frame...
                self._blinker = not self._blinker

            self.radius = self._frames_since_detonated * self.GROW_RATE

            color = self.EXPLOSION_COLOR_1 if self._blinker else self.EXPLOSION_COLOR_2
            self._circlesurf.set_alpha(self._get_alpha())

            # Set the radius based on the number of frames since 100 (so it grows every frame)
            pygame.draw.circle(self._circlesurf, color, (self.rect.centerx, self.rect.centery), self.radius)
            mainsurf.blit(self._circlesurf, (0, 0))
        else:
            # We are past the radius, so we do not draw, and we set this.done to True
            # so the main game loop knows it can remove this from the list of bombs.
            self.done = True

class TimeBomb(Bomb):
    GROW_RATE = 30
    EXPLOSION_COLOR_1 = (100, 100, 255)
    EXPLOSION_COLOR_2 = (50, 50, 255)
    BLAST_RADIUS = 5000
    FUSE = 20

    def __init__(self, x, y):
        super().__init__(x, y)

        self.image = pygame.image.load("images/timebomb.png")
        self.rect = pygame.rect.Rect((x, y), self.image.get_size())

    def _get_alpha(self):
        ratio_done = self.radius / self.BLAST_RADIUS

        # Fade out from 255 down based on how far along we are in the explosion.
        # But don't go below 20, so we can always see some blue
        return max(255 * (1 - ratio_done), 20)

    def get_time_scale(self):
        return 0.3



class StarField(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()

        self.image = pygame.Surface((WIDTH, HEIGHT))
        self.rect = pygame.rect.Rect((0, 0), self.image.get_size())

        y = 0
        while y < HEIGHT:
            x = 0
            while x < WIDTH:
                if random.randint(0, 100) == 0:
                    startype = random.choice(['white', 'red', 'blue'])
                    if startype == 'white':
                        color = (255, 255, 255)
                    elif startype == 'red':
                        color = (random.randint(150, 255), 50, 50)
                    elif startype == 'blue':
                        color = (50, 50, random.randint(150, 255))

                    self.image.set_at((x, y), color)
                x += 1
            y += 1

    def draw(self):
        mainsurf.blit(self.image, self.rect)

def showlevel(level):
    textsurf = mainfont.render(str(level), True, MAIN_COLOR)
    mainsurf.blit(textsurf, (WIDTH - 50, 50))

def showboostbar(boostleft):
    width = (boostleft / MAX_BOOST) * BOOST_BAR_WIDTH

    if boostleft < MIN_BOOST:
        color = BOOST_BAR_COLOR_DEPLETED
    else:
        color = BOOST_BAR_COLOR

    # The x position of the bar is the width of the screen, minus the width of the bar
    # (so it doesn't go off the screen), minus another 30px so it's not right up
    # against the edge of the screen.
    barx = WIDTH - BOOST_BAR_WIDTH - 30

    # y position is 20px (just a little bit of padding so it's not right at the top)
    bary = 20

    # The width of the bar is the percentage of boost that we have left, times the width
    # of the full bar. So if we're at 50% boost and the full bar is 150 pixels, then
    # we display a bar 75 pixels wide.
    barwidth = (boostleft / MAX_BOOST) * BOOST_BAR_WIDTH

    # The height is just a constant
    barheight = BOOST_BAR_HEIGHT

    # Time to draw the bar!
    pygame.draw.rect(mainsurf, color, (barx, bary, barwidth, barheight))

    # Now, let's make the line that marks the minimum boost level

    # To compute the x position for the minimum boost line, we take 3 steps:
    #   - First, we divide the minimum boost over the maximum boost, to find out
    #     how far along the bar we should draw the line (as a ratio). For example,
    #     if MIN_BOOST is 20 and MAX_BOOST is 100, then the ratio would be 0.2.
    #   - Next, we multiply this ratio by the width of the bar to get the actual
    #     number of pixels.
    #   - Finally, we add the x position of the bar to push the whole thing to the
    #     right so it lines up with the bar.
    linex = ((MIN_BOOST / MAX_BOOST) * BOOST_BAR_WIDTH) + barx

    # Line y position is the same as bar
    liney = bary

    # Line is 2 pixels wide
    linewidth = 2

    # Line is same height as bar
    lineheight = barheight

    pygame.draw.rect(mainsurf, BOOST_BAR_LINE_COLOR, (linex, liney, linewidth, lineheight))

losescreen = None
winscreen = None
pausescreen = None

powerups = {
    'bomb': BombPowerup(),
    'shield': ShieldPowerup(),
    'timebomb': TimeBombPowerup()
}
starfield = StarField()

rocket = Rocket()
cookie = Cookie()
shield = None

# Create first devil
devils.append(Devil())
while True:
    event = pygame.event.poll()     
 
    if event.type == QUIT:
        exit()
 
    if gamewon:
        if winscreen is None:
            winscreen = WinScreen()
        winscreen.draw()
        pygame.display.update()
        continue

    if gamelost:
        if losescreen is None:
            losescreen = LoseScreen()

        losescreen.draw()
        pygame.display.update()
        continue

    if event.type == KEYUP and event.key == K_ESCAPE:  # If the player just pressed escape...
        paused = not paused  # Flip paused state

        if paused:
            pausescreen = PauseScreen()
        else:
            pausescreen = None

    # If the game is paused, display the pause screen and skip everything else
    if paused:
        pausescreen.draw()
        pygame.display.update()
        continue

    keyspressed = pygame.key.get_pressed()

    ### Update rocket speed

    # If the player pressed "b" and we have enough boost to start, then go into boost mode
    if event.type == KEYDOWN and event.key == K_b and boostleft > MIN_BOOST:
        boostmode = True
        rocketspeed = 20

    if event.type == KEYUP and event.key == K_b:  # Boost mode over
        boostmode = False
        rocketspeed = 1

    if boostmode:
        # We're in boost mode

        boostleft -= 1  # Deplete the boost counter
        if boostleft <= 0:
            boostmode = False
            rocketspeed = 1
    else:
        # We're not in boost mode

        # Replenish boost counter
        if boostleft <= MAX_BOOST:
            boostleft += 0.25

        # If space is held down, increase rocket speed (but don't let the speed go over the max)
        if keyspressed[K_SPACE]:
            rocketspeed += .25
            if rocketspeed > MAX_SPEED:
                rocketspeed = MAX_SPEED

        # If shift is held down, decrease rocket speed (but don't let the speed go under 0)
        if keyspressed[K_LSHIFT] or keyspressed[K_RSHIFT]:
            rocketspeed -= 1
            if rocketspeed < 0:
                rocketspeed = .1

    ### Update rocket position using the speed we just calculated

    if keyspressed[K_UP]:
        rocket.rect.y -= rocketspeed
 
    if keyspressed[K_DOWN]:
        rocket.rect.y += rocketspeed
 
    if keyspressed[K_LEFT]:
        rocket.rect.x -= rocketspeed
 
    if keyspressed[K_RIGHT]:
        rocket.rect.x += rocketspeed

    # If the rocket is now past the edge in any direction, move it back to the edge.
    if rocket.rect.x < 0:
        rocket.rect.x = 0

    if rocket.rect.x > WIDTH - rocket.rect.width:
        rocket.rect.x = WIDTH - rocket.rect.width

    if rocket.rect.y < 0:
        rocket.rect.y = 0

    if rocket.rect.y > HEIGHT - rocket.rect.height:
        rocket.rect.y = HEIGHT - rocket.rect.height
    

    ### Update devil positions

    i = 0
    while i < len(devils): # For each devil...
        # Get the current x and y position for this devil
        devil = devils[i]

        # If there is a time bomb and it's exploding, we ask it for a time
        # scale to find out how much to slow down the world.
        if timebomb is not None and timebomb.exploding:
            timescale = timebomb.get_time_scale()
        else:
            timescale = 1

        # Calculate the *new* x and y position for this devil
        if devil.rect.x > rocket.rect.x:
            devil.rect.x -= DEVILSPEED * timescale
    
        if devil.rect.x < rocket.rect.x:
            devil.rect.x += DEVILSPEED * timescale
     
        if devil.rect.y > rocket.rect.y:
            devil.rect.y -= DEVILSPEED * timescale
     
        if devil.rect.y < rocket.rect.y:
            devil.rect.y += DEVILSPEED * timescale

        devilgroup.remove(devil)
        collidingdevil = pygame.sprite.spritecollideany(devil, devilgroup)
        devilgroup.add(devil)


        if collidingdevil is not None:
            rd = randomdirection()
            dirx = rd[0]
            diry = rd[1]

            devil.rect.x += dirx
            devil.rect.y += diry

        i += 1

    if event.type == KEYDOWN and event.key == K_d:
        for bomb in bombs:
            bomb.detonate()

    # For each of the powerup objects...
    for powerup in powerups.values():
        # If we are colliding with this powerup and it hasn't been
        # collected already, collect it.
        if rocket.rect.colliderect(powerup.rect) and powerup.state == 'onscreen':
            powerup.collect()

    ### We have the new positions for everything. Now, check for collisions and update the game in response

    # Check if the rocket is colliding with any of the devils. If so, we lost
    i = 0
    while i < len(devils):
        devil = devils[i]

        if rocket.rect.colliderect(devil.rect):
            gamelost = True
            break
        i += 1

    if gamelost:
        losesound.play()
        continue

    # Check for collisions with bombs.
    for bomb in bombs:
        if bomb.exploding and pygame.sprite.collide_circle(bomb, rocket):
            # If the rocket is colliding with an exploding bomb, we lose
            gamelost = True
            continue

        for devil in list(devils):
            # If a devil is colliding with an exploding bomb, it goes bye-bye
            if bomb.exploding and pygame.sprite.collide_circle(bomb, devil):
                devils.remove(devil)
                devilgroup.remove(devil)

    if event.type == KEYDOWN and event.key == K_d:
        for bomb in bombs:
            bomb.detonate()


    if gamelost:
        losesound.play()
        continue
 
    # Check if the rocket is colliding with the cookie
    if rocket.rect.colliderect(cookie.rect):
        # Time to level up!
        level += 1

        if level > MAX_POINTS:  # We won
            gamewon = True
            winsound.play()
            continue
        else:
            cookie = Cookie()
            if level == MAX_POINTS:  # Final level
                devilgroup.empty()
                devils = [BossDevil()]
            else:
                for i in range(level):
                    devils.append(Devil())
            levelupsound.play()

            # If there's a powerup for this level, drop it.
            if level in LEVEL_TO_POWERUP: 
                # There is a powerup in the table for this level.
                # So get the powerup's name
                powerupname = LEVEL_TO_POWERUP[level]

                # Now, look up the actual powerup object and tell it to drop
                powerups[powerupname].drop()

    if event.type == KEYUP and event.key == K_RETURN and powerups['bomb'].state == 'collected':  # Drop a bomb
        bombs.append(Bomb(rocket.rect.x, rocket.rect.y))

    # Clear out bombs that have finished detonating
    for bomb in list(bombs):
        if bomb.done:
            bombs.remove(bomb)

    if (event.type == KEYDOWN and event.key == K_t and timebomb is None
        and powerups['timebomb'].state == 'collected'):
        timebomb = TimeBomb(rocket.rect.x, rocket.rect.y)

    if timebomb is not None and timebomb.done:
        timebomb = None

    if shield is not None:
        if shield.done:
            shield = None
        else:
            for devil in devils:
                if pygame.sprite.collide_circle(devil, shield):
                    # OK, we need to move the devil outward past the edge of the shield.
   
                    # Get the difference between this devil and the center of the shield along
                    # the x and y axes. You can also think of this as a vector of the two numbers
                    # "dx" and "dy"
                    dx = devil.rect.centerx - rocket.rect.centerx
                    dy = devil.rect.centery - rocket.rect.centery

                    # Convert the difference along the x and y axis to a distance
                    # (You can also think of this as the length of a vector)
                    len_xy = math.sqrt(dx**2 + dy**2)


                    # Divide each component of the vector by the length so it is "normalized"
                    # to a vector with a length between 0 and 1
                    if len_xy == 0:
                        # Don't want to divide by zero
                        dx_normalized = dy_normalized = 0
                    else:
                        dx_normalized = dx / len_xy
                        dy_normalized = dy / len_xy

                    # We will push the devil out just enough to get it to the edge --
                    # we start with the radius of the shield, then subtract the distance
                    # of the devil from the center. We also add 5 pixels as a "fudge factor"
                    # so it's not sitting right on the edge.

                    pushdistance = shield.radius - len_xy + 5

                    # Add the appropriate distance to each dimension, multiplying by the 
                    # normalized vector from before to make sure it goes out at the same
                    # angle.
                    devil.rect.centerx += dx_normalized * pushdistance
                    devil.rect.centery += dy_normalized * pushdistance

    if (event.type == KEYDOWN and event.key == K_s and shield is None and
        powerups['shield'].state == 'collected'):
        shield = Shield(rocket)

    ### The game state has been updated. Time to render!

    starfield.draw()

    showlevel(level)
    showboostbar(boostleft)

    # Render rocket and cookie
    cookie.draw()

    for bomb in bombs:
        bomb.draw()

    for powerup in powerups.values():
        if powerup.state == 'onscreen':
            powerup.draw()

    if timebomb is not None:
        timebomb.draw()

    # Render devils
    i = 0
    while i < len(devils):
        devil = devils[i]
        devil.draw()
        i += 1

    rocket.draw()

    if shield is not None:
        shield.draw()

    pygame.display.update()
