from .client import CourseTracker


class User(CourseTracker):
    def add_track(self, course_id: str) -> None:
        return super().add_track(course_id)

    def delete_track(self, course_id: str) -> None:
        return super().delete_track(course_id)

    def get_track(self) -> list:
        return super().get_tracks()
