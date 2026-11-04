# Lưu trữ dữ liệu về giảng viên
class Professor:
    """Giảng viên: hai thông tin mà giải thuật dùng.

    Subjects  — tập ID môn dạy được, quyết định không gian gen "gán giảng viên"
                (Schedule._randomProfessorFor chỉ rút trong những giảng viên có
                môn của lớp).
    BusySlots — tập ô (ngày, offset) giảng viên đã bận. Đây là đầu vào duy nhất
                của ràng buộc mềm B: mỗi lớp bị xếp vào một ô bận của chính giảng
                viên được gán cho nó sẽ mất Criteria.busyPenalty = 0.2 điểm.
                SốBusySlots càng lớn thì lịch càng dễ bị phạt, nên bộ dữ liệu mẫu
                giới hạn mỗi giảng viên không quá 10 tiết bận mỗi tuần.
    """
    # Khởi tạo dữ liệu giảng viên
    # subjects: tập ID các môn giảng viên có khả năng giảng dạy (phụ trách)
    # busy: tập (ngày, chỉ số khung giờ 0-based) mà giảng viên bận trong tuần;
    #       chỉ số này KHÔNG phải số tiết hiển thị (buổi chiều lệch nhau 1)
    #       và là nguồn duy nhất về lịch bận — các khối {day, start, end} trong
    #       tệp cấu hình được bung ra đây ngay khi đọc tệp.
    def __init__(self, id, name, subjects=None, busy=None):
        self.Id = id
        self.Name = name
        # Các môn có khả năng giảng dạy (phụ trách), lưu ID môn học. Dùng set để
        # việc tra canTeach và dựng tra cứu môn -> giảng viên không trùng lặp.
        self.Subjects = set(subjects) if subjects else set()
        # Các ô (ngày, khung giờ) bận cố định trong tuần, dạng tập (day, time)
        # với time là offset 0-based; isBusyAt tra trực tiếp nên chi phí O(1).
        self.BusySlots = set(busy) if busy else set()

    # Kiểm tra giảng viên có khả năng giảng dạy môn học với ID được cho không
    def canTeach(self, courseId):
        return courseId in self.Subjects

    # Kiểm tra ô (ngày, tiết) có nằm trong khung bận của giảng viên không
    # Cả hai phía phải dùng cùng hệ offset 0-based (0..12, 6 là nghỉ trưa)
    def isBusyAt(self, day, time):
        return (day, time) in self.BusySlots


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