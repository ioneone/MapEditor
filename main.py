import pygame
from pygame.locals import *
import os
import struct
import sys
import codecs

TILE_SIZE = 32
ROW = 20
COLUMN = 25
SCREEN_RECT = Rect(0, 0, TILE_SIZE*COLUMN, TILE_SIZE*ROW)
INPUT_RECT = Rect(240, 302, 320, 36)

show_grid = False
background_img = 'water.png'
map_chip_list = []

GREEN = (0, 255, 0)

""" How to use

Press 'SPACE' to select tile
Press 'S' to save file
Press 'L' to load file
Press 'N' to create a new file
Press 'G' to show grid line
Press 'R' to move the cursor to (0, 0)

Left-click to place the selected tile

"""


def main():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_RECT.size)
    pygame.display.set_caption("Map Editor")
    
    # Load map chip
    # load_mapchips("data", "mapchip.dat")
    load_map_chips("mapchip")
    
    palette = MapchipPalette()
    map = Map("NEW", 64, 64, palette)
    cursor = Cursor(0, 0)
    message_engine = MessageEngine()
    input_window = InputWindow(INPUT_RECT, message_engine)
    
    clock = pygame.time.Clock()

    while True:
        clock.tick(60)
        if palette.display_flag:
            # draw palette
            palette.update()
            palette.draw(screen)
        else:
            # draw map
            offset = calc_offset(cursor)
            """ updates """
            cursor.update()
            map.update(offset)
            """ render """
            map.draw(screen, offset)
            cursor.draw(screen, offset)
            # draw selected map chip
            screen.blit(Map.images[palette.selected_mapchip], (10, 10))
            pygame.draw.rect(screen, GREEN, (10, 10, 32, 32), 3)
            # show the position of the mouse cursor
            px, py = pygame.mouse.get_pos()
            selectx = (px + offset[0]) / TILE_SIZE
            selecty = (py + offset[1]) / TILE_SIZE
            message_engine.draw_string(screen, (10, 56), map.name)
            message_engine.draw_string(screen, (10, 86), "%d　%d" % (selectx, selecty))
        pygame.display.update()
        """ input """
        for event in pygame.event.get():
            if event.type == QUIT:  # if x button was pressed
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == K_SPACE:
                    palette.display_flag = not palette.display_flag
                elif event.key == K_g:
                    global show_grid
                    show_grid = not show_grid
                elif event.key == K_n:
                    try:
                        name = input_window.ask(screen, "NAME?")
                        row = int(input_window.ask(screen, "ROW?"))
                        col = int(input_window.ask(screen, "COL?"))
                        default = int(input_window.ask(screen, "DEFAULT?"))
                    except ValueError:
                        print("Cannot create map")
                        continue
                    map = Map(name, row, col, default, palette)
                elif event.key == K_s:
                    name = input_window.ask(screen, "SAVE?")
                    map.save(name)
                elif event.key == K_l:
                    try:
                        name = input_window.ask(screen, "LOAD?")
                        map.load(name)
                    except IOError:
                        print("Cannot load: %s" % name)
                        continue
                elif event.key == K_r:
                    cursor.x, cursor.y = 0, 0


class Cursor:
    COLOR = GREEN
    WIDTH = 3

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.rect = Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def update(self):
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_DOWN]:
            self.y += 1
        elif pressed_keys[K_LEFT]:
            self.x -= 1
        elif pressed_keys[K_RIGHT]:
            self.x += 1
        elif pressed_keys[K_UP]:
            self.y -= 1
        self.rect = Rect(self.x*TILE_SIZE, self.y*TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def draw(self, screen, offset):
        offset_x, offset_y = offset
        px = self.rect.topleft[0]
        py = self.rect.topleft[1]
        pygame.draw.rect(screen, self.COLOR, (px-offset_x, py-offset_y, TILE_SIZE, TILE_SIZE), self.WIDTH)


class Map:

    images = []
    default = 0  # id number of the default map chip
    out_of_range_chip = 0

    def __init__(self, name, row, col, palette):
        self.name = name
        self.row = row
        self.col = col
        self.map = [[Map.default for c in range(self.col)] for r in range(self.row)]  # two dimensional arrays
        self.palette = palette

    def update(self, offset):
        offset_x, offset_y = offset
        mouse_pressed = pygame.mouse.get_pressed()
        if mouse_pressed[0]:  # left-click
            # get local position of the mouse
            px, py = pygame.mouse.get_pos()
            # convert local coordinates to world coordinates
            selectx = int((px + offset_x) / TILE_SIZE)
            selecty = int((py + offset_y) / TILE_SIZE)
            # if out of the map
            if selectx < 0 or selecty < 0 or selectx > self.col-1 or selecty > self.row-1:
                return
            # change clicked tile
            self.map[selecty][selectx] = self.palette.selected_mapchip
        elif mouse_pressed[2]:  # right-click
            px, py = pygame.mouse.get_pos()
            selectx = int((px + offset_x) / TILE_SIZE)
            selecty = int((py + offset_y) / TILE_SIZE)
            if selectx < 0 or selecty < 0 or selectx > self.col-1 or selecty > self.row-1:
                return
            self.palette.selected_mapchip = self.map[selecty][selectx]

    def draw(self, screen, offset):
        offset_x, offset_y = offset
        # calculate how far the map should be drawn
        startx = int(offset_x / TILE_SIZE) - 1
        endx = int(startx + SCREEN_RECT.width/TILE_SIZE + 2)
        starty = int(offset_y / TILE_SIZE)
        endy = int(starty + SCREEN_RECT.height/TILE_SIZE + 2)
        # draw
        for y in range(starty, endy):
            for x in range(startx, endx):
                # if out of the map, draw 'none' image
                if x < 0 or y < 0 or x > self.col-1 or y > self.row-1:
                    screen.blit(self.images[Map.out_of_range_chip], (x*TILE_SIZE-offset_x,y*TILE_SIZE-offset_y))
                else:
                    # draw the default map chip first so that the transparency works
                    screen.blit(self.images[Map.default], (x * TILE_SIZE - offset_x, y * TILE_SIZE - offset_y))
                    screen.blit(self.images[self.map[y][x]], (x*TILE_SIZE-offset_x, y*TILE_SIZE-offset_y))

                    if show_grid:
                        pygame.draw.rect(screen, (0, 0, 0), (x*TILE_SIZE-offset_x, y*TILE_SIZE-offset_y, TILE_SIZE, TILE_SIZE), 1)

    def save(self, name):

        #  Author: Junhong Wang
        #  Date: 2016/11/01
        #  Description: update the map to a new coordinates
        new_images = []
        new_images.append("none.png")
        new_images.append(background_img)
        for r in range(self.row):
            for c in range(self.col):
                map_chip_id = self.map[r][c]
                image_name = map_chip_list[map_chip_id+1]
                try:
                    new_images.index(image_name)
                except ValueError:
                    new_images.append(image_name)
                self.map[r][c] = new_images.index(image_name)

        self.default = new_images.index(background_img)

        """ save the map chip data """
        new_map_chip_file_name = name.lower()+".dat"
        new_map_chip_file = open(new_map_chip_file_name,'w')
        for i in range(0, len(new_images)):
            new_map_chip_file.write(str(i)+","+new_images[i][:-4]+","+"0\n")
        new_map_chip_file.close()


        """ save the map with binary format """
        file = "%s.map" % (name.lower())
        fp = open(file, "wb")  # open with binary mode
        # "i" int
        fp.write(struct.pack("i", self.row))
        fp.write(struct.pack("i", self.col))
        # "B" unsigned char
        fp.write(struct.pack("B", self.default))
        for r in range(row):
            for c in range(self.col):
                fp.write(struct.pack("B", self.map[r][c]))
        fp.close()

        self.palette.selected_mapchip = 0
        self.load(name)

    def load(self, name):


        #  Author: Junhong Wang
        #  Date: 2016/11/01
        #  Description: load the map chip with the new coordinate system
        """ read map chip data file """
        load_resized_map_chips(name.lower()+".dat")

        """ read binary map """
        file = "%s.map" % (name.lower())
        fp = open(file, "rb")
        self.name = name

        row = struct.unpack("i", fp.read(struct.calcsize("i")))[0]
        self.col = struct.unpack("i", fp.read(struct.calcsize("i")))[0]
        self.default = struct.unpack("B", fp.read(struct.calcsize("B")))[0]
        self.map = [[self.default for c in range(self.col)] for r in range(row)]
        for r in range(row):
            for c in range(self.col):
                self.map[r][c] = struct.unpack("B", fp.read(struct.calcsize("B")))[0]
        fp.close()


class MapchipPalette:
    """ map chip palette """
    COLOR = GREEN
    WIDTH = 3

    def __init__(self):
        self.display_flag = False
        self.selected_mapchip = 0

    def update(self):
        mouse_pressed = pygame.mouse.get_pressed()
        if mouse_pressed[0]:  # left-click
            mouse_pos = pygame.mouse.get_pos()
            # convert mouse position to palette position
            x = int(mouse_pos[0] / TILE_SIZE)
            y = int(mouse_pos[1] / TILE_SIZE)
            # convert palette position to map chip id
            n = y * COLUMN + x
            if n < len(Map.images) and Map.images[n]:
                self.selected_mapchip = n
                self.display_flag = False
                # prevent the clicking to be effective right after the palette disappear
                pygame.time.wait(500)

    def draw(self, screen):
        for i in range(ROW * COLUMN):
            x = int(i % COLUMN) * TILE_SIZE
            y = int(i / COLUMN) * TILE_SIZE
            image = Map.images[Map.out_of_range_chip]
            try:
                if Map.images[i]:
                    image = Map.images[i]
            except IndexError:
                image = Map.images[Map.out_of_range_chip]

            screen.blit(Map.images[Map.out_of_range_chip], (x, y))
            screen.blit(image, (x, y))
        mouse_pos = pygame.mouse.get_pos()
        x = int(mouse_pos[0] / TILE_SIZE)
        y = int(mouse_pos[1] / TILE_SIZE)
        pygame.draw.rect(screen, self.COLOR, (x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE), self.WIDTH)


def load_image(dir, file):
    file = os.path.join(dir, file)
    image = pygame.image.load(file)
    image = image.convert_alpha()
    return image


def calc_offset(cursor):
    offset_x = cursor.rect.topleft[0] - SCREEN_RECT.width/2
    offset_y = cursor.rect.topleft[1] - SCREEN_RECT.height/2
    return offset_x, offset_y


def load_resized_map_chips(file_path):

    #  Author: Junhong Wang
    #  Date: 2016/11/01
    #  Description: clear the lists before loading the new map chip
    Map.images.clear()
    map_chip_list.clear()

    fp = open(file_path, "r")
    for line in fp:
        line = line.rstrip()  # get rid of blank line
        data = line.split(",")
        id = int(data[0])
        name = data[1]
        Map.images.append(load_image("mapchip", "%s.png" % name))
        if name == 'none':
            try:
                Map.out_of_range_chip = id
            except ValueError:
                pass
        elif name == background_img[:-4]:
            try:
                Map.default = id
            except ValueError:
                pass
        movable = int(data[2])
    fp.close()


def load_map_chips(directory):

    #  Author: Junhong Wang
    #  Date: 2016/11/01
    #  Description: clear the lists before loading the new map chip
    Map.images.clear()
    map_chip_list.clear()

    image_list = os.listdir(directory)
    global map_chip_list
    map_chip_list = image_list
    print(image_list)
    for i in range(1, len(image_list)):
        if image_list[i] == 'none.png':
            Map.out_of_range_chip = i-1
        elif image_list[i] == background_img:
            Map.default = i-1
        Map.images.append(load_image(directory, image_list[i]))


class MessageEngine:
    
    FONT_WIDTH = 16
    FONT_HEIGHT = 22
    WHITE, RED, GREEN, BLUE = 0, 160, 320, 480

    def __init__(self):
        self.image = load_image("data", "font.png")
        self.color = self.WHITE
        self.kana2rect = {}
        self.create_hash()

    def set_color(self, color):

        self.color = color
        if not self.color in [self.WHITE, self.RED, self.GREEN, self.BLUE]:
            self.color = self.WHITE

    def draw_character(self, screen, pos, ch):
        x, y = pos
        try:
            rect = self.kana2rect[ch]
            screen.blit(self.image, (x, y), (rect.x+self.color, rect.y, rect.width, rect.height))
        except KeyError:
            print("描画できない文字があります:%s" % ch)
            return

    def draw_string(self, screen, pos, str):
        x, y = pos
        for i, ch in enumerate(str):
            dx = x + self.FONT_WIDTH * i
            self.draw_character(screen, (dx, y), ch)

    def create_hash(self):
        filepath = os.path.join("data", "kana2rect.dat")
        fp = codecs.open(filepath, "r", "utf-8")
        for line in fp.readlines():
            line = line.rstrip()
            d = line.split(" ")
            kana, x, y, w, h = d[0], int(d[1]), int(d[2]), int(d[3]), int(d[4])
            self.kana2rect[kana] = Rect(x, y, w, h)
        fp.close()


class Window:

    EDGE_WIDTH = 4

    def __init__(self, rect):
        self.rect = rect
        self.inner_rect = self.rect.inflate(-self.EDGE_WIDTH*2, -self.EDGE_WIDTH*2)
        self.is_visible = False

    def draw(self, screen):
        """ウィンドウを描画"""
        if not self.is_visible:
            return
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 0)
        pygame.draw.rect(screen, (0, 0, 0), self.inner_rect, 0)

    def show(self):
        self.is_visible = True

    def hide(self):
        self.is_visible = False


class InputWindow(Window):
    def __init__(self, rect, message_engine):
        Window.__init__(self, rect)
        self.message_engine = message_engine

    def get_key(self):
        while True:
            event = pygame.event.poll()
            if event.type == KEYDOWN:
                return event.key
            else:
                pass

    def draw(self, screen, message):
        Window.draw(self, screen)
        if len(message) != 0:
            self.message_engine.draw_string(screen, self.inner_rect.topleft, message)
            pygame.display.flip()

    def ask(self, screen, question):
        cur_str = []
        self.show()
        self.draw(screen, question)
        while True:
            key = self.get_key()
            if key == K_BACKSPACE:
                cur_str = cur_str[0:-1]
            elif key == K_ESCAPE:
                return None
            elif key == K_RETURN:
                break
            elif K_0 <= key <= K_9 or K_a <= key <= K_z:
                cur_str.append(chr(key).upper())
            self.draw(screen, question + u"　" + "".join(cur_str))
        return "".join(cur_str)

if __name__ == "__main__":
    main()
