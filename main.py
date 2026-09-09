import asyncio
import curses
import random
import time
from itertools import cycle
from pathlib import Path

from curses_tools import draw_frame, get_frame_size, read_controls
from physics import update_speed
from space_garbage import fly_garbage

TIC_TIMEOUT = 0.1
COROUTINES = []


def read_frame(filename, directory=Path('frames/')):
    file_path = directory / filename
    with open(file_path, 'r') as file:
        frame = file.read()
    return frame


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def fill_orbit_with_garbage(canvas, garbage_frames, offset_tics):
    _, columns_number = canvas.getmaxyx()
    border_offset = 1
    while True:
        await sleep(offset_tics)
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
    row_speed = column_speed = 0
    while True:
        row_direction, column_direction, space_pressed = read_controls(canvas)

        if space_pressed:
            await run_spaceship(canvas, row, column, frame_column)

        row_speed, column_speed = update_speed(
            row_speed,
            column_speed,
            row_direction,
            column_direction,
            fading=0.8,
        )
        row += row_speed
        column += column_speed

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


async def run_spaceship(canvas, row, column, frame_column_size):
    starship_centre = round(frame_column_size / 2)
    column = column + starship_centre
    coroutine = fire(canvas, row, column)
    COROUTINES.append(coroutine)


async def blink(
    canvas,
    row,
    column,
    offset_tics,
    symbol='*',
):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)
        await sleep(offset_tics)
        canvas.addstr(row, column, symbol)
        await sleep(3)
        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)
        canvas.addstr(row, column, symbol)
        await sleep(3)


def draw(canvas, starship_frame_1, starship_frame_2, garbage_frames):
    window_height, window_width = canvas.getmaxyx()
    stars = '+*.:'
    border_offset = 2
    for _ in range(60):
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

    COROUTINES.append(fill_orbit_with_garbage(canvas, garbage_frames, 10))

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
