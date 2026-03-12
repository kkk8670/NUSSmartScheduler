from fastapi import APIRouter


router = APIRouter()


@router.get("/schedule")
def get_schedule():
    return {
        "plans": [
            {"title": "Safe", "desc": "Avoid lateness", "meta": "Score 128.4", "active": True},
            {"title": "Tight", "desc": "Minimize idle", "meta": "Score 132.7", "active": False},
            {"title": "Min-Walk", "desc": "Reduce walking", "meta": "Score 126.9", "active": False},
        ],
        "timeline": [
            {"title": "ISS Orientation Class", "loc": "ISS Inspire Theatre", "start": "09:00", "end": "10:30", "travel": "10′", "color": "indigo"},
            {"title": "Lunch @ The Deck", "loc": "Canteen · The Deck", "start": "12:10", "end": "13:10", "travel": "12′", "color": "emerald"},
            {"title": "Study · LeetCode", "loc": "MSL Library", "start": "13:30", "end": "15:00", "travel": "6′", "color": "sky"},
            {"title": "Gym (Cardio)", "loc": "USC Gym", "start": "18:45", "end": "19:45", "travel": "16′", "color": "rose"},
            {"title": "Review & Notes", "loc": "Dorm", "start": "20:15", "end": "22:15", "travel": "14′", "color": "amber"},
        ]
    }