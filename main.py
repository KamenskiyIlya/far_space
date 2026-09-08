import asyncio
import curses
import random
import time
from itertools import cycle
from pathlib import Path

from curses_tools import draw_frame, get_frame_size, read_controls
from space_garbage import fly_garbage

TIC_TIMEOUT = 0.1
COROUTINES = []


def read_frame(filename, directory=Path('frames/')):
    file_path = directory / filename
    with open(file_path, 'r') as file:
        frame = file.read()
    return frame


async def fill_orbit_with_garbage(canvas, garbage_frames, offset_tics):
    _, columns_number = canvas.getmaxyx()
    border_offset = 1
    while True:
        for _ in range(offset_tics):
            await asyncio.sleep(0)
        garbage_frame = random.choice(garbage_frames)
        _, frame_columns = get_frame_size(garbage_frame)

        right_limit = columns_number - border_offset - frame_columns
        column = random.randint(border_offset, right_limit)
        COROUTINES.append(fly_garbage(canvas, column, garbage_frame))


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


async def animate_spaceship(canvas, frame_1, frame_2, row, column):
    frames = cycle([frame_1, frame_1, frame_2, frame_2])
    frame_row, frame_column = get_frame_size(frame_1)
    window_row, window_column = canvas.getmaxyx()
    border_offset = 1
    while True:
        row_direction, column_direction, _ = read_controls(canvas)
        row += row_direction
        column += column_direction

        row = max(row, border_offset)
        row = min(row, window_row - frame_row - border_offset)
        column = max(
            border_offset,
            min(column, window_column - frame_column - border_offset),
        )
        column = max(column, border_offset)
        column = min(column, window_column - frame_column - border_offset)

        frame = next(frames)
        draw_frame(canvas, row, column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, frame, negative=True)


async def blink(
    canvas,
    row,
    column,
    offset_tics,
    symbol='*',
):
    while True:
        for _ in range(20):
            canvas.addstr(row, column, symbol, curses.A_DIM)
            await asyncio.sleep(0)

        for _ in range(offset_tics):
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


def draw(canvas, starship_frame_1, starship_frame_2, garbage_frames):
    window_height, window_width = canvas.getmaxyx()
    stars = '+*.:'
    border_offset = 2
    for _ in range(120):
        rand_height = random.randint(
            border_offset, window_height - border_offset
        )
        rand_width = random.randint(
            border_offset, window_width - border_offset
        )
        rand_star = random.choice(stars)
        rand_tick = random.randint(1, 10)
        coroutine = blink(
            canvas,
            rand_height,
            rand_width,
            rand_tick,
            rand_star,
        )
        COROUTINES.append(coroutine)

    center_row = window_height // 2
    center_column = window_width // 2
    starship_height, starship_width = get_frame_size(starship_frame_1)
    starship_start_row = center_row - (starship_height // 2)
    starship_start_column = center_column - (starship_width // 2)

    COROUTINES.append(
        animate_spaceship(
            canvas,
            starship_frame_1,
            starship_frame_2,
            starship_start_row,
            starship_start_column,
        )
    )

    COROUTINES.append(fill_orbit_with_garbage(canvas, garbage_frames, 7))

    canvas.nodelay(True)
    curses.curs_set(False)

    while True:
        for coroutine in COROUTINES.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)
        canvas.border()
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    starship_frame_1 = read_frame('rocket_frame_1.txt')
    starship_frame_2 = read_frame('rocket_frame_2.txt')

    garbage_path = Path('frames/garbage')
    garbage_frames = [
        read_frame(frame.name, garbage_path)
        for frame in garbage_path.glob('*.txt')
    ]

    curses.update_lines_cols()
    curses.wrapper(draw, starship_frame_1, starship_frame_2, garbage_frames)
