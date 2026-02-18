import requests
from mcp.server.fastmcp import FastMCP
from typing import Optional, Literal

mcp = FastMCP("Kowloon Motor Bus Service")

stops: list[dict] = []

def stops_setup() -> bool:
    global stops
    response = requests.get("https://data.etabus.gov.hk/v1/transport/kmb/stop")
    try:
        response.raise_for_status()
        stops = response.json()["data"]
        stops.sort(key=lambda stop: stop["long"])
    except Exception:
        return False
    return True

def select(long: float, direction:Literal["left", "right"], begin: int, end: int) -> Optional[int]:
    if begin >= end:
        return None
    if begin - end == -1:
        if direction == "left" and stops[begin]["long"] <= long or \
          direction == "right" and stops[begin]["long"] >= long:
            return begin
        return None
    match direction:
        case "left":
            if int(stops[int((begin + end) / 2)]["long"]) <= long:
                print(1)
                return select(long, direction, int((begin + end) / 2), end)
            else:
                print(2)
                return select(long, direction, begin, int((begin + end) / 2))
        case "right":
            if int(stops[int((begin + end - 1) / 2)]["long"]) < long:
                return select(long, direction, int((begin + end - 1) / 2) + 1, end)
            else:
                return select(long, direction, begin, int((begin + end - 1) / 2) + 1)
            
def find(long: float, lat:float, max=0.005) -> Optional[int]:
    left = select(long - max, 'right', 0, len(stops))
    right = select(long + max, 'left', 0, len(stops))
    distance = lambda plong, plat: ((plong - long) ** 2 + (plat - lat) ** 2) ** 0.5
    if left == None or right == None or left > right:
        return None
    min = (right, distance(stops[right]["long"], stops[right]["lat"]))
    for i in range(left, right):
        if min > distance(stops[i]["long"], stops[i]["lat"]):
            min = distance(stops[i]["long"], stops[i]["lat"])
    return min[0]

@mcp.tool()
def lltoeta(long: float, lat: float, route:str) -> str:
    """
    Get the estimated arrival time of the next bus, at given position, for given route.
    
    :param long: The longtitude of the bus station.
    :type long: float
    :param lat: The latitude of the bus station.
    :type lat: float
    :param route: The requested route.
    :type route: str
    :return: The estimated arrival time of the next bus.
    :rtype: str
    """
    stop = find(long, lat)
    if stop == None:
        return "No KMS bus stops within 500m."
    response = requests.get("https://data.etabus.gov.hk/v1/transport/kmb/stop-eta/" + stops[stop]["stop"])
    try:
        response.raise_for_status()
        response = response.json()["data"]
    except Exception:
        return "Failed to fetch ETA of desired stop."
    result = "No bus will arrive within half an hour in estimation."
    for record in response:
        if record["route"] == route:
            result = f"""
Bus stop: {stops[stop]["name_en"]}
Route: {record["route"]}
ETA: {record["eta"]}
"""
    return result

@mcp.tool()
def stoptoeta(name: str, route: str):
    """
    Get the estimated arrival time of the next bus, at given stop, for given route.
    
    :param name: The name of the bus stop.
    :type name: str
    :param route: The requested route.
    :type route: str
    """
    stop = -1
    for i in range(len(stops)):
        if name.lower() in stops[i]["name_en"].lower():
            stop = i
    if stop == -1:
        return "No bus stop of given name."
    response = requests.get("https://data.etabus.gov.hk/v1/transport/kmb/stop-eta/" + stops[stop]["stop"])
    try:
        response.raise_for_status()
        response = response.json()["data"]
    except Exception:
        return "Failed to fetch ETA of desired stop."
    result = "No bus will arrive within half an hour in estimation."
    for record in response:
        if record["route"] == route:
            result = f"""
Bus stop: {stops[stop]["name_en"]}
Route: {record["route"]}
ETA: {record["eta"]}
"""
    return result

if not stops_setup():
    print("Failed to fetch list of stops")
    exit(-1)

mcp.run()
