import asyncio
import curses
import random
import time
from itertools import cycle

from curses_tools import draw_frame, get_frame_size, read_controls

TIC_TIMEOUT = 0.1


async def blink(canvas, row, column, symbol='*'):
    while True:
        for _ in range(20):
            canvas.addstr(row, column, symbol, curses.A_DIM)
            await asyncio.sleep(0)

        for _ in range(random.randint(1, 10)):
            await asyncio.sleep(0)

        for _ in range(3):
            canvas.addstr(row, column, symbol)
            await asyncio.sleep(0)

        for _ in range(5):
            canvas.addstr(row, column, symbol, curses.A_BOLD)
            await asyncio.sleep(0)

        for _ in range(3):
            canvas.addstr(row, column, symbol)
            await asyncio.sleep(0)


def draw(canvas, starship_frame_1, starship_frame_2):
    window_height, window_width = canvas.getmaxyx()
    coroutines = []
    stars = '+*.:'
    for _ in range(120):
        rand_height = random.randint(2, window_height - 2)
        rand_width = random.randint(2, window_width - 2)
        rand_star = random.choice(stars)
        coroutine = blink(canvas, rand_height, rand_width, rand_star)
        coroutines.append(coroutine)

    center_row = window_height // 2
    center_column = window_width // 2
    starship_height, starship_width = get_frame_size(starship_frame_1)
    starship_start_row = center_row - (starship_height // 2)
    starship_start_column = center_column - (starship_width // 2)

    coroutines.append(
        animate_spaceship(
            canvas,
            starship_frame_1,
            starship_frame_2,
            starship_start_row,
            starship_start_column,
        )
    )

    canvas.nodelay(True)
    curses.curs_set(False)
    canvas.border()
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


async def fire(
    canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0
):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


def read_frame(filename):
    with open(f'frames/{filename}', 'r') as file:
        frame = file.read()
    return frame


async def animate_spaceship(canvas, frame_1, frame_2, row, column):
    frames = cycle([frame_1, frame_2])
    frame_row, frame_column = get_frame_size(frame_1)
    window_row, window_column = canvas.getmaxyx()
    minimal_row, minimal_column = 1, 1
    border_size = 1
    while True:
        row_direction, column_direction, _ = read_controls(canvas)
        row += row_direction
        column += column_direction

        row = max(minimal_row, min(row, window_row - frame_row - border_size))
        column = max(
            minimal_column,
            min(column, window_column - frame_column - border_size),
        )

        frame = next(frames)
        draw_frame(canvas, row, column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, frame, negative=True)


if __name__ == '__main__':
    starship_frame_1 = read_frame('rocket_frame_1.txt')
    starship_frame_2 = read_frame('rocket_frame_2.txt')
    curses.update_lines_cols()
    curses.wrapper(draw, starship_frame_1, starship_frame_2)
