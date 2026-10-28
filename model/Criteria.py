from .Constant import Constant


# Đọc tệp cấu hình và lưu các đối tượng đã phân tích
class Criteria:
    # Trọng số phạt cho từng tiêu chí, theo thứ tự P (phòng),
    # G (giảng viên), N (nghỉ trưa).
    # 0 = không phạt, 1 = phạt tối đa (mất trọn 1 điểm của tiêu chí).
    # Điểm của một tiêu chí: đạt = 1; vi phạm = 1 - weight.
    weights = [1.0, 1.0, 1.0]

    # kiểm tra các lớp học phần có bị trùng phòng hay không
    @staticmethod
    def isRoomOverlapped(slots, reservation, dur):
        reservation_index = hash(reservation)
        cls = slots[reservation_index: reservation_index + dur]
        return any(True for slot in cls if len(slot) > 1)

    # kiểm tra sự trùng lặp giữa các lớp học phần về giảng viên
    @staticmethod
    def isOverlappedProf(slots, cc, numberOfRooms, timeId):
        po = False

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
                        # đã phát hiện trùng lịch giảng viên thì dừng kiểm tra
                        if po:
                            return po

            timeId += Constant.DAY_HOURS
        return po

    # kiểm tra lớp học phần có rơi vào khung giờ nghỉ trưa (12h-13h) không
    @staticmethod
    def isInLunchBreak(timeId, dur):
        # lớp học vi phạm nếu bất kỳ tiết nào của nó nằm trong khung nghỉ trưa
        return timeId <= Constant.LUNCH_PERIOD < timeId + dur

    # Trọng số phạt cho một vi phạm ràng buộc mềm (soft constraint).
    # Ràng buộc mềm không bắt buộc phải đạt, chỉ làm giảm điểm số của nhiễm sắc thể.
    softPenalty = 0.25
    # Giảng viên được dạy tối đa bao nhiêu tiết trong một ngày (ràng buộc mềm).
    maxProfHoursPerDay = 6

    # kiểm tra ràng buộc mềm: giảng viên dạy quá nhiều tiết trong ngày không?
    @staticmethod
    def isProfessorDailyOverloaded(hoursPerDay, professorId, day):
        return hoursPerDay.get((professorId, day), 0) > Criteria.maxProfHoursPerDay
