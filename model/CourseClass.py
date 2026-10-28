class CourseClass:
    # Bộ đếm ID được dùng để gán ID tự động
    _next_class_id = 0

    # Khởi tạo đối tượng lớp học phần
    def __init__(self, professor, course, duration):
        self.Id = CourseClass._next_class_id
        CourseClass._next_class_id += 1
        # Trả về con trỏ tới giảng viên giảng lớp này
        self.Professor = professor
        # Trả về con trỏ tới môn học mà lớp học phần này thuộc về
        self.Course = course
        # Trả về thời lượng của lớp học phần tính bằng giờ
        self.Duration = duration

        # liên kết giảng viên với lớp học phần
        self.Professor.addCourseClass(self)

    # Trả về TRUE nếu hai lớp học phần có cùng giảng viên.
    def professorOverlaps(self, c):
        return self.Professor == c.Professor

    def __hash__(self):
        return hash(self.Id)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return hash(self) == hash(other)

    def __ne__(self, other):
        # Không thực sự cần thiết, nhưng để tránh việc x==y và x!=y
        # cùng trả về True
        return not (self == other)

    # Khởi động lại việc gán ID
    @staticmethod
    def restartIDs() -> None:
        CourseClass._next_class_id = 0
