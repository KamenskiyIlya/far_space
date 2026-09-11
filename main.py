import asyncio
import curses
import random
import time
from itertools import cycle
from pathlib import Path

from curses_tools import draw_frame, get_frame_size, read_controls
from explosion import explode
from game_scenario import get_garbage_delay_tics
from obstacles import OBSTACLES, OBSTACLES_IN_LAST_COLLISIONS
from physics import update_speed
from space_garbage import fly_garbage

TIC_TIMEOUT = 0.05
COROUTINES = []
YEAR = 1957


async def year_counter_by_time(canvas, secs):
    global YEAR
    rows_number, columns_number = canvas.getmaxyx()
    scoreboard_height = 2
    text_right_margin = 1
    subboard_rows, subboard_columns = (
        scoreboard_height,
        columns_number - text_right_margin,
    )
    subboard_start_row, subboard_start_column = (
        rows_number - scoreboard_height,
        text_right_margin,
    )
    year_board = canvas.derwin(
        subboard_rows,
        subboard_columns,
        subboard_start_row,
        subboard_start_column,
    )
    year_msg_row, year_msg_column = 0, 1
    tics_per_year = int(secs / TIC_TIMEOUT)
    while True:
        for _ in range(tics_per_year):
            year_board.addstr(year_msg_row, year_msg_column, f'Year: {YEAR}')
            await sleep(1)
        YEAR += 1


def read_frame(filename, directory=Path('frames/')):
    file_path = directory / filename
    with open(file_path, 'r') as file:
        frame = file.read()
    return frame


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def fill_orbit_with_garbage(canvas, garbage_frames):
    _, columns_number = canvas.getmaxyx()
    border_offset = 1
    while True:
        delay = get_garbage_delay_tics(YEAR)
        await sleep(delay if delay else 1)
        if not delay:
            continue
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
        for obstacle in OBSTACLES:
            if obstacle.has_collision(
                row,
                column,
            ):
                OBSTACLES_IN_LAST_COLLISIONS.append(obstacle)
                center_row = obstacle.row + obstacle.rows_size / 2
                center_column = obstacle.column + obstacle.columns_size / 2
                COROUTINES.append(explode(canvas, center_row, center_column))
                return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def show_gameover(canvas, gameover_frame):
    rows_number, columns_number = canvas.getmaxyx()
    center_row = rows_number / 2
    center_column = columns_number / 2

    row_size, column_size = get_frame_size(gameover_frame)
    corner_row = round(center_row - row_size / 2)
    corner_column = round(center_column - column_size / 2)
    while True:
        draw_frame(canvas, corner_row, corner_column, gameover_frame)
        await asyncio.sleep(0)


async def animate_spaceship(
    canvas, frame_1, frame_2, row, column, gameover_frame
):
    frames = cycle([frame_1, frame_1, frame_2, frame_2])
    frame_row, frame_column = get_frame_size(frame_1)
    rows_number, columns_number = canvas.getmaxyx()
    border_offset = 1
    row_speed = column_speed = 0
    while True:
        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column, frame_row, frame_column):
                OBSTACLES_IN_LAST_COLLISIONS.append(obstacle)

                center_row = obstacle.row + obstacle.rows_size / 2
                center_column = obstacle.column + obstacle.columns_size / 2
                COROUTINES.append(explode(canvas, center_row, center_column))

                starship_center_row = row + round(frame_row / 2)
                starship_center_column = column + round(frame_column / 2)
                COROUTINES.append(
                    explode(
                        canvas, starship_center_row, starship_center_column
                    )
                )

                await show_gameover(canvas, gameover_frame)

        row_direction, column_direction, space_pressed = read_controls(canvas)

        if space_pressed and YEAR >= 2020:
            COROUTINES.append(
                spaceship_shooting(canvas, row, column, frame_column)
            )

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
        row = min(row, rows_number - frame_row - border_offset)
        column = max(
            border_offset,
            min(column, columns_number - frame_column - border_offset),
        )
        column = max(column, border_offset)
        column = min(column, columns_number - frame_column - border_offset)

        frame = next(frames)
        draw_frame(canvas, row, column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, frame, negative=True)


async def spaceship_shooting(canvas, row, column, frame_column_size):
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


def fill_orbit_with_start(canvas, count=60):
    rows_number, columns_number = canvas.getmaxyx()
    stars = '+*.:'
    border_offset = 1
    scoreboard_height = 2
    for _ in range(count):
        rand_height = random.randint(
            border_offset, rows_number - scoreboard_height - border_offset
        )
        rand_width = random.randint(
            border_offset, columns_number - border_offset
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


def draw(
    canvas, starship_frame_1, starship_frame_2, garbage_frames, gameover_frame
):
    rows_number, columns_number = canvas.getmaxyx()

    COROUTINES.append(year_counter_by_time(canvas, secs=1.5))

    fill_orbit_with_start(canvas)

    center_row = rows_number // 2
    center_column = columns_number // 2
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
            gameover_frame,
        )
    )

    COROUTINES.append(fill_orbit_with_garbage(canvas, garbage_frames))

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

    gameover_frame = read_frame('game_over.txt')

    curses.update_lines_cols()
    curses.wrapper(
        draw,
        starship_frame_1,
        starship_frame_2,
        garbage_frames,
        gameover_frame,
    )
