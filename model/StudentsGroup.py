# Lưu trữ dữ liệu về nhóm sinh viên
class StudentsGroup:
    # Khởi tạo dữ liệu nhóm sinh viên
    def __init__(self, id, name, numberOfStudents):
        self.Id = id
        self.Name = name
        self.NumberOfStudents = numberOfStudents
        self.CourseClasses = []

    # Liên kết nhóm với lớp học phần
    def addClass(self, course_class):
        self.CourseClasses.append(course_class)

    def __hash__(self):
        return hash(self.Id)

    # So sánh ID của hai đối tượng đại diện cho nhóm sinh viên
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return hash(self) == hash(other)

    def __ne__(self, other):
        # Không thực sự cần thiết, nhưng để tránh việc x==y và x!=y
        # cùng trả về True
        return not (self == other)