"""STOP MESSAGE TEXT
Helper to generate the Stop Message text body
"""

# # Native # #
import datetime

# # Project # #
from ...persistence_api import saved_stops
from ...static_handler import *
from ...entities import *

__all__ = ("generate_stop_message_text",)


def generate_stop_message_text(stop: Stop, buses: Buses, user_saved_stop: saved_stops.SavedStopBase) -> str:
    messages = get_messages()

    # Generate Stop Name text
    if user_saved_stop and user_saved_stop.stop_name:
        stop_name_text = messages.stop.stop_custom_name.format(
            stop_custom_name=user_saved_stop.stop_name,
            stop_original_name=stop.name
        )
    else:
        stop_name_text = stop.name

    # Generate Buses text
    if buses:
        buses_text_lines = list()
        for bus in buses:
            if bus.time == 0:
                time_text = messages.stop.bus_time_now
            else:
                time_text = messages.stop.bus_time_remaining.format(minutes=bus.time)
            buses_text_lines.append(messages.stop.bus_line.format(
                line=bus.line,
                route=bus.route,
                time=time_text
            ))
        buses_text = "\n".join(buses_text_lines)
    else:
        buses_text = messages.stop.no_buses_found

    last_update_text = datetime.datetime.now().strftime(messages.stop.time_format)

    return messages.stop.message.format(
        stop_id=stop.stopid,
        stop_name=stop_name_text,
        buses=buses_text,
        last_update=last_update_text
    )
