import asyncio

from curses_tools import draw_frame, get_frame_size
from obstacles import OBSTACLES, OBSTACLES_IN_LAST_COLLISIONS, Obstacle


async def fly_garbage(canvas, column, garbage_frame, speed=0.25):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()
    column = max(column, 0)
    column = min(column, columns_number - 1)
    row = 0

    rows_size, columns_size = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, column, rows_size, columns_size)
    OBSTACLES.append(obstacle)

    try:
        while row < rows_number:
            if obstacle in OBSTACLES_IN_LAST_COLLISIONS:
                OBSTACLES_IN_LAST_COLLISIONS.remove(obstacle)
                return
            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
            obstacle.row = row
    finally:
        OBSTACLES.remove(obstacle)
