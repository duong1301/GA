# Lưu trữ dữ liệu về giảng viên
class Professor:
    # Khởi tạo dữ liệu giảng viên
    # subjects: tập ID các môn giảng viên có khả năng giảng dạy (phụ trách)
    # busy: tập (ngày, chỉ số khung giờ 0-based) mà giảng viên bận trong tuần;
    #       chỉ số này KHÔNG phải số tiết hiển thị (buổi chiều lệch nhau 1)
    #       và là nguồn duy nhất về lịch bận — các khối {day, start, end} trong
    #       tệp cấu hình được bung ra đây ngay khi đọc tệp.
    def __init__(self, id, name, subjects=None, busy=None):
        self.Id = id
        self.Name = name
        # Các môn có khả năng giảng dạy (phụ trách), lưu ID môn học
        self.Subjects = set(subjects) if subjects else set()
        # Các ô (ngày, khung giờ) bận cố định trong tuần, dạng tập (day, time)
        self.BusySlots = set(busy) if busy else set()

    # Kiểm tra giảng viên có khả năng giảng dạy môn học với ID được cho không
    def canTeach(self, courseId):
        return courseId in self.Subjects

    # Kiểm tra ô (ngày, tiết) có nằm trong khung bận của giảng viên không
    def isBusyAt(self, day, time):
        return (day, time) in self.BusySlots

    # Kiểm tra ô (ngày, tiết) có nằm trong giờ giảng viên RẢI (không bận) không
    def isAvailableAt(self, day, time):
        return (day, time) not in self.BusySlots

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