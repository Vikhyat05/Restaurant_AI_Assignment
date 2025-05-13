# from typing import Sequence, Union, List
# from datetime import datetime, time


# def _lower_list(val: Union[None, str, Sequence[str]]) -> List[str]:
#     if val is None:
#         return []
#     return [
#         v.lower().strip()
#         for v in (
#             val if isinstance(val, Sequence) and not isinstance(val, str) else [val]
#         )
#     ]


# def _to_time(val: Union[str, datetime, time]) -> time:
#     """Accept 'HH:MM', datetime, or time → naive `time` object (24-h clock)."""
#     if isinstance(val, time):
#         return val
#     if isinstance(val, datetime):
#         return val.time()
#     return datetime.strptime(val, "%H:%M" if len(val) == 5 else "%H:%M:%S").time()


# def _inside_range(t: time, start: time, end: time) -> bool:
#     """Return True if `t` is between start & end, handling overnight ranges."""
#     if start <= end:  # normal same-day range
#         return start <= t <= end
#     return t >= start or t <= end  # overnight, e.g. 18:00-02:00
