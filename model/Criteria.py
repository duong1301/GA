from .Constant import Constant


# Đọc tệp cấu hình và lưu các đối tượng đã phân tích
class Criteria:
    # Trọng số phạt cho từng tiêu chí, theo thứ tự P (phòng), C (chỗ),
    # G (giảng viên), S (sinh viên).
    # 0 = không phạt, 1 = phạt tối đa (mất trọn 1 điểm của tiêu chí).
    # Điểm của một tiêu chí: đạt = 1; vi phạm = 1 - weight.
    weights = [1.0, 0.5, 1.0, 1.0]

    # kiểm tra các lớp học phần có bị trùng phòng hay không
    @staticmethod
    def isRoomOverlapped(slots, reservation, dur):
        reservation_index = hash(reservation)
        cls = slots[reservation_index: reservation_index + dur]
        return any(True for slot in cls if len(slot) > 1)

    # phòng hiện tại có đủ chỗ ngồi không
    @staticmethod
    def isSeatEnough(r, cc):
        return r.NumberOfSeats >= cc.NumberOfSeats

    # kiểm tra sự trùng lặp giữa các lớp học phần về giảng viên và nhóm sinh viên
    @staticmethod
    def isOverlappedProfStudentGrp(slots, cc, numberOfRooms, timeId):
        po = go = False

        dur = cc.Duration
        for i in range(numberOfRooms, 0, -1):
            # với từng giờ của lớp học phần
            for j in range(timeId, timeId + dur):
                cl = slots[j]
                for cc1 in cl:
                    if cc != cc1:
                        # giảng viên có bị trùng lịch không?
                        if not po and cc.professorOverlaps(cc1):
                            po = True
                        # nhóm sinh viên có bị trùng lịch không?
                        if not go and cc.groupsOverlap(cc1):
                            go = True
                        # cả hai loại trùng lặp? không cần kiểm tra thêm
                        if po and go:
                            return po, go

            timeId += Constant.DAY_HOURS
        return po, go