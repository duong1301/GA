# Lưu trữ dữ liệu về giảng viên
class Professor:
    # Khởi tạo dữ liệu giảng viên
    def __init__(self, id, name):
        self.Id = id
        self.Name = name
        self.CourseClasses = []

    # Liên kết giảng viên với lớp học phần
    def addCourseClass(self, courseClass):
        self.CourseClasses.append(courseClass)

    def __hash__(self):
        return hash(self.Id)

    # So sánh ID của hai đối tượng đại diện cho giảng viên
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return hash(self) == hash(other)

    def __ne__(self, other):
        # Không thực sự cần thiết, nhưng để tránh việc x==y và x!=y
        # cùng trả về True
        return not (self == other)